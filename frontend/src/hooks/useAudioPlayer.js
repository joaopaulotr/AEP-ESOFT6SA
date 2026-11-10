import { useCallback, useEffect, useRef, useState } from "react";

const espera = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Toca áudios em sequência. `play(blob)` toca um (interrompendo o atual); `enfileirar` coloca
 * áudios (ainda sendo gerados) numa fila tocada estritamente em ordem. `stop()` cancela a fila
 * inteira e o áudio atual (barge-in, sair da tela, trocar para texto).
 * `ocupado` fica true enquanto há algo tocando OU esperando na fila (não pisca entre frases).
 */
export function useAudioPlayer() {
    const audioRef = useRef(null);
    const urlRef = useRef(null);
    const resolveRef = useRef(null);
    const geracaoRef = useRef(0);
    const cadeiaRef = useRef(Promise.resolve());
    const pendentesRef = useRef(0);
    const montadoRef = useRef(true);
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

    return { play, enfileirar, aguardarFila, stop, tocando, ocupado };
}
