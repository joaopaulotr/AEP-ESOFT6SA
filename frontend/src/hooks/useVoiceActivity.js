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

/** Fator sobre o nível de eco medido durante a reprodução (limiar do barge-in = max(base, eco * k)). */
export const FATOR_ECO = 1.8;
const IGNORAR_INICIO_FRASE_MS = 250; // o início de cada frase tocada é ignorado (pico do eco)
const MEDIR_ECO_MS = 500;

function percentil(leituras, p) {
    const o = [...leituras].sort((a, b) => a - b);
    return o[Math.floor((o.length - 1) * p)] ?? 0;
}

/**
 * Detecção de atividade de voz sobre um MediaStream (AnalyserNode, RMS a cada ~50 ms).
 * `modo`:
 *  - "ocioso": mede o volume (`nivelRef`, usado pela onda) e mantém uma estimativa móvel do
 *    ruído de fundo (só amostras abaixo do limiar entram, então a fala não a contamina).
 *  - "gravacao": chama `aoSilencio` após 1,2 s de silêncio, depois de >= 600 ms de fala. Usa a
 *    estimativa de ruído já existente (não recalibra durante a fala da pessoa).
 *  - "barge": só deve ser pedido enquanto um <audio> está de fato tocando. Ignora os primeiros
 *    250 ms de cada frase, mede o eco (percentil 90 do RMS por 500 ms) uma vez e o mantém entre as
 *    frases do mesmo turno (zera ao entrar em "gravacao"); limiar = max(0,02, ruído*2,5, eco*1,8).
 *    Chama `aoFalaContinua` com > 300 ms de fala contínua.
 * `contexto`: AudioContext criado no gesto do usuário (quem cria também fecha); sem ele a hook cria um.
 */
export function useVoiceActivity({ stream, contexto, modo = "ocioso", aoFalaContinua, aoSilencio }) {
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
        if (!stream || (!contexto && !Ctx)) return undefined;

        const ctx = contexto || new Ctx();
        const proprio = !contexto;
        ctx.resume?.().catch(() => {});
        const fonte = ctx.createMediaStreamSource(stream);
        const analisador = ctx.createAnalyser();
        analisador.fftSize = 1024;
        fonte.connect(analisador);
        const buf = new Float32Array(analisador.fftSize);

        const aberto = Date.now();
        const primeiras = [];
        let ambiente = null; // ruído de fundo (RMS)
        let eco = null; // nível de eco durante a reprodução
        let ecoLeituras = [];
        let modoAtual = null;
        let modoInicio = 0;
        let ultimo = aberto;
        let falaMs = 0;
        let continuaMs = 0;
        let silencioMs = 0;
        let disparou = false;

        const id = setInterval(() => {
            analisador.getFloatTimeDomainData(buf);
            const rms = rmsDe(buf);
            nivelRef.current = rms;
            const t = Date.now();
            const dt = t - ultimo;
            ultimo = t;

            if (ambiente === null) {
                primeiras.push(rms);
                if (t - aberto >= VAD.calibracaoMs) ambiente = ruidoDeFundo(primeiras);
            }
            const ruido = ambiente ?? ruidoDeFundo(primeiras);
            const base = Math.min(VAD.limiarMaximo, Math.max(VAD.limiarMinimo, ruido * VAD.fatorRuido));

            if (modoRef.current !== modoAtual) {
                modoAtual = modoRef.current;
                modoInicio = t;
                falaMs = continuaMs = silencioMs = 0;
                disparou = false;
                if (modoAtual === "gravacao") {
                    eco = null; // a pessoa falou: o próximo turno mede o eco de novo
                    ecoLeituras = [];
                }
            }

            if (modoAtual === "ocioso") {
                if (ambiente !== null && rms <= base) ambiente = ambiente * 0.97 + rms * 0.03;
                return;
            }

            let limiar = base;
            if (modoAtual === "barge") {
                const decorrido = t - modoInicio;
                if (decorrido < IGNORAR_INICIO_FRASE_MS) return;
                if (eco === null) {
                    ecoLeituras.push(rms);
                    if (decorrido >= IGNORAR_INICIO_FRASE_MS + MEDIR_ECO_MS) eco = percentil(ecoLeituras, 0.9);
                    return;
                }
                limiar = Math.max(base, eco * FATOR_ECO);
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
            if (proprio) ctx.close?.().catch(() => {});
        };
    }, [stream, contexto]);

    return { nivelRef };
}
