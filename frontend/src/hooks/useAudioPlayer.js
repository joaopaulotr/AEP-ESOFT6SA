import { useCallback, useEffect, useRef, useState } from "react";

export function useAudioPlayer() {
    const audioRef = useRef(null);
    const urlRef = useRef(null);
    const resolveRef = useRef(null);
    const [tocando, setTocando] = useState(false);

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

    const stop = useCallback(() => {
        liberar();
        setTocando(false);
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

                const terminou = () => stop();
                audio.onended = terminou;
                audio.onerror = terminou;

                setTocando(true);
                audio.play().catch(terminou); // autoplay bloqueado → segue o fluxo
            }),
        [liberar, stop]
    );

    // Para o áudio ao sair da tela.
    useEffect(() => stop, [stop]);

    return { play, stop, tocando };
}
