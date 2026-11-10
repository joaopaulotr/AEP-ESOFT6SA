import { useCallback, useRef } from "react";
import { api } from "../services/api";

export const FRASES_FILLER = [
    "Hmm, entendi…",
    "Certo…",
    "Aham…",
    "Sei…",
    "Entendi, deixa eu pensar…",
    "Que interessante…",
];
export const ESPERA_FILLER_MS = 700; // só toca se a 1ª frase não chegou até aqui
export const PROBABILIDADE_FILLER = 0.5; // no máximo ~metade dos turnos

/**
 * Cache dos áudios de filler ("Hmm, entendi…"), gerados na abertura da entrevista com o tom da
 * persona. Falhas de TTS são ignoradas (o filler simplesmente não existe).
 */
export function useFillers() {
    const blobsRef = useRef(new Map()); // texto -> Blob (só os que já chegaram)
    const ultimoRef = useRef(null);
    const preparadoRef = useRef(false);

    const preparar = useCallback((tom) => {
        preparadoRef.current = true;
        blobsRef.current = new Map();
        FRASES_FILLER.forEach((texto) => {
            api.synthesizeSpeech(texto, tom)
                .then((blob) => blobsRef.current.set(texto, blob))
                .catch(() => {});
        });
    }, []);

    /**
     * Sorteia um filler pronto (nunca o mesmo da vez anterior) ou devolve null: sem sorte
     * (probabilidade 0,5) ou sem nada pronto. `aleatorio` existe para teste.
     */
    const sortear = useCallback((aleatorio = Math.random) => {
        if (aleatorio() >= PROBABILIDADE_FILLER) return null;
        const candidatos = [...blobsRef.current.keys()].filter((t) => t !== ultimoRef.current);
        if (!candidatos.length) return null;
        const texto = candidatos[Math.floor(aleatorio() * candidatos.length)];
        ultimoRef.current = texto;
        return { texto, blob: blobsRef.current.get(texto) };
    }, []);

    return { preparar, sortear, preparadoRef };
}
