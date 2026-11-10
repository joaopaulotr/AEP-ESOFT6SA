import { useCallback, useEffect, useRef, useState } from "react";

const espera = (ms) => new Promise((r) => setTimeout(r, ms));

// EV-80: volume da voz da IA sem rotear a saída pelo AudioContext (mantém o cancelamento de eco
// do barge-in). O áudio é decodificado à parte e vira uma lista de volumes (RMS) por janela de 30 ms;
// durante a reprodução, o volume é lido pela posição atual do <audio>.
const JANELA_S = 0.03;

async function calcularEnvelope(blob) {
    const Offline = window.OfflineAudioContext || window.webkitOfflineAudioContext;
    if (!Offline) return null;
    const dados = await blob.arrayBuffer();
    const buffer = await new Offline(1, 1, 44100).decodeAudioData(dados);
    const canal = buffer.getChannelData(0);
    const passo = Math.max(1, Math.round(buffer.sampleRate * JANELA_S));
    const envelope = new Float32Array(Math.ceil(canal.length / passo));
    for (let j = 0; j < envelope.length; j++) {
        let soma = 0;
        const fim = Math.min(canal.length, (j + 1) * passo);
        for (let k = j * passo; k < fim; k++) soma += canal[k] * canal[k];
        envelope[j] = Math.sqrt(soma / Math.max(1, fim - j * passo));
    }
    return envelope;
}

/**
 * Toca áudios em sequência. `play(blob)` toca um (interrompendo o atual); `enfileirar` coloca
 * áudios (ainda sendo gerados) numa fila tocada estritamente em ordem. `stop()` cancela a fila
 * inteira e o áudio atual (barge-in, sair da tela, trocar para texto).
 * `ocupado` fica true enquanto há algo tocando OU esperando na fila (não pisca entre frases).
 * `nivelRef.current` (EV-80): volume (RMS) da voz da IA no instante atual; 0 sem áudio tocando,
 * null enquanto o volume do áudio atual ainda não foi calculado.
 */
export function useAudioPlayer() {
    const audioRef = useRef(null);
    const urlRef = useRef(null);
    const resolveRef = useRef(null);
    const geracaoRef = useRef(0);
    const cadeiaRef = useRef(Promise.resolve());
    const pendentesRef = useRef(0);
    const montadoRef = useRef(true);
    const envelopeRef = useRef(null); // EV-80
    const [nivelRef] = useState(() => ({
        get current() {
            const audio = audioRef.current;
            if (!audio) return 0;
            const env = envelopeRef.current;
            if (!env) return null;
            return env[Math.min(env.length - 1, Math.floor(audio.currentTime / JANELA_S))] ?? 0;
        },
    }));
    const [tocando, setTocando] = useState(false);
    const [ocupado, setOcupado] = useState(false);

    const liberar = useCallback(() => {
        const audio = audioRef.current;
        if (audio) {
            audio.onended = null;
            audio.onerror = null;
            audio.pause();
        }
        audioRef.current = null;
        envelopeRef.current = null;

        if (urlRef.current) {
            URL.revokeObjectURL(urlRef.current);
            urlRef.current = null;
        }

        // Garante que quem está esperando o play() não fique travado.
        const resolve = resolveRef.current;
        resolveRef.current = null;
        resolve?.();
    }, []);

    const encerrarAtual = useCallback(() => {
        liberar();
        if (montadoRef.current) setTocando(false);
    }, [liberar]);

    const stop = useCallback(() => {
        geracaoRef.current += 1; // invalida tudo o que está na fila
        cadeiaRef.current = Promise.resolve();
        pendentesRef.current = 0;
        liberar();
        if (montadoRef.current) {
            setTocando(false);
            setOcupado(false);
        }
    }, [liberar]);

    const play = useCallback(
        (blob) =>
            new Promise((resolve) => {
                liberar(); // interrompe o que estiver tocando

                const url = URL.createObjectURL(blob);
                const audio = new Audio(url);
                urlRef.current = url;
                audioRef.current = audio;
                resolveRef.current = resolve;

                // EV-80: calcula o volume desse áudio em paralelo (não atrasa o início da fala).
                calcularEnvelope(blob)
                    .then((env) => {
                        if (audioRef.current === audio) envelopeRef.current = env;
                    })
                    .catch(() => {});

                audio.onended = encerrarAtual;
                audio.onerror = encerrarAtual;

                setTocando(true);
                audio.play().catch(encerrarAtual); // autoplay bloqueado → segue o fluxo
            }),
        [liberar, encerrarAtual]
    );

    /**
     * `fonte`: Blob ou Promise<Blob> (falha = pula, a legenda segue). `aoIniciar` roda quando a vez
     * dele chega. `naoAntesDe`: timestamp (Date.now()) antes do qual não começa (atraso de "pensar").
     * Devolve uma Promise que resolve quando esse item termina (ou é cancelado).
     */
    const enfileirar = useCallback(
        (fonte, { aoIniciar, naoAntesDe } = {}) => {
            const geracao = geracaoRef.current;
            pendentesRef.current += 1;
            setOcupado(true);
            const item = cadeiaRef.current.then(async () => {
                if (geracao !== geracaoRef.current) return;
                let blob = null;
                try {
                    blob = await fonte;
                } catch {
                    blob = null;
                }
                if (naoAntesDe) {
                    const falta = naoAntesDe - Date.now();
                    if (falta > 0) await espera(falta);
                }
                if (geracao !== geracaoRef.current) return;
                aoIniciar?.();
                if (blob && blob.size > 0) await play(blob); // áudio vazio: só a legenda (evita erro do <audio>)
            });
            cadeiaRef.current = item.finally(() => {
                if (geracao !== geracaoRef.current) return;
                pendentesRef.current = Math.max(0, pendentesRef.current - 1);
                if (pendentesRef.current === 0 && montadoRef.current) setOcupado(false);
            });
            return item;
        },
        [play]
    );

    /** Resolve quando a fila esvaziar (ou for cancelada). */
    const aguardarFila = useCallback(() => cadeiaRef.current, []);

    // Para o áudio ao sair da tela.
    useEffect(() => {
        montadoRef.current = true;
        return () => {
            montadoRef.current = false;
            stop();
        };
    }, [stop]);

    return { play, enfileirar, aguardarFila, stop, tocando, ocupado, nivelRef };
}