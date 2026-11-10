import { useEffect, useRef } from "react";

// Valores fixados pela pesquisa (docs/EVOLUCOES.md, seção 5).
export const VAD = {
    intervaloMs: 50, // frequência de leitura do volume
    calibracaoMs: 500, // janela inicial que mede o ruído de fundo
    limiarMinimo: 0.02, // RMS mínimo para contar como fala
    fatorRuido: 2.5, // limiar = max(mínimo, ruído de fundo * fator)
    limiarMaximo: 0.15, // teto, para um ambiente barulhento não deixar o limiar inalcançável
    minFalaMs: 600, // fala mínima antes de o silêncio poder encerrar a gravação
    silencioMs: 1200, // silêncio que encerra a gravação
    bargeInMs: 300, // fala contínua que interrompe a IA
};

function rmsDe(buf) {
    let soma = 0;
    for (let i = 0; i < buf.length; i++) soma += buf[i] * buf[i];
    return Math.sqrt(soma / buf.length);
}

/** Ruído de fundo = percentil 25 das leituras da janela (se a pessoa já estiver falando, não contamina). */
function ruidoDeFundo(leituras) {
    const ordenadas = [...leituras].sort((a, b) => a - b);
    return ordenadas[Math.floor((ordenadas.length - 1) * 0.25)] ?? 0;
}

/**
 * Detecção de atividade de voz sobre um MediaStream (AnalyserNode, RMS a cada ~50 ms).
 * `modo`:
 *  - "ocioso": só mede o volume (`nivelRef`, usado pela onda).
 *  - "gravacao": chama `aoSilencio` após 1,2 s de silêncio, depois de >= 600 ms de fala.
 *  - "barge": chama `aoFalaContinua` quando há > 300 ms de fala contínua (a IA está falando).
 * A cada troca de modo o limiar é recalibrado nos primeiros 500 ms; em "barge" isso inclui o
 * áudio de saída que escapa do cancelamento de eco, o que mantém o limiar acima dele.
 * Devolve `nivelRef` (RMS atual, 0..1). O AudioContext é fechado ao sair/trocar de stream.
 */
export function useVoiceActivity({ stream, modo = "ocioso", aoFalaContinua, aoSilencio }) {
    const nivelRef = useRef(0);
    const modoRef = useRef(modo);
    modoRef.current = modo;
    const aoFalaRef = useRef(aoFalaContinua);
    aoFalaRef.current = aoFalaContinua;
    const aoSilencioRef = useRef(aoSilencio);
    aoSilencioRef.current = aoSilencio;

    useEffect(() => {
        nivelRef.current = 0;
        const Ctx = typeof window !== "undefined" && (window.AudioContext || window.webkitAudioContext);
        if (!stream || !Ctx) return undefined;

        const ctx = new Ctx();
        ctx.resume?.().catch(() => {});
        const fonte = ctx.createMediaStreamSource(stream);
        const analisador = ctx.createAnalyser();
        analisador.fftSize = 1024;
        fonte.connect(analisador);
        const buf = new Float32Array(analisador.fftSize);

        let modoAtual = null;
        let inicio = 0;
        let ultimo = 0;
        let leituras = [];
        let limiar = null;
        let falaMs = 0;
        let continuaMs = 0;
        let silencioMs = 0;
        let disparou = false;

        const id = setInterval(() => {
            analisador.getFloatTimeDomainData(buf);
            const rms = rmsDe(buf);
            nivelRef.current = rms;

            const t = Date.now();
            if (modoRef.current !== modoAtual) {
                modoAtual = modoRef.current;
                inicio = t;
                ultimo = t;
                leituras = [];
                limiar = null;
                falaMs = continuaMs = silencioMs = 0;
                disparou = false;
            }
            if (modoAtual === "ocioso") return;

            const dt = t - ultimo;
            ultimo = t;
            if (limiar === null) {
                leituras.push(rms);
                if (t - inicio >= VAD.calibracaoMs) {
                    limiar = Math.min(VAD.limiarMaximo, Math.max(VAD.limiarMinimo, ruidoDeFundo(leituras) * VAD.fatorRuido));
                }
                return;
            }

            if (rms > limiar) {
                falaMs += dt;
                continuaMs += dt;
                silencioMs = 0;
            } else {
                continuaMs = 0;
                silencioMs += dt;
            }
            if (disparou) return;
            if (modoAtual === "barge" && continuaMs >= VAD.bargeInMs) {
                disparou = true;
                aoFalaRef.current?.();
            } else if (modoAtual === "gravacao" && falaMs >= VAD.minFalaMs && silencioMs >= VAD.silencioMs) {
                disparou = true;
                aoSilencioRef.current?.();
            }
        }, VAD.intervaloMs);

        return () => {
            clearInterval(id);
            nivelRef.current = 0;
            try {
                fonte.disconnect();
            } catch {
                // já desconectado
            }
            ctx.close?.().catch(() => {});
        };
    }, [stream]);

    return { nivelRef };
}
