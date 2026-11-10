import { useCallback, useRef } from "react";
import { api } from "../services/api";

// Só sons curtos e neutros: tocam antes de qualquer fala, inclusive do acolhimento (nada de
// "Que interessante…" antes de uma resposta delicada).
export const FRASES_FILLER = ["Hmm…", "Certo…", "Aham…", "Entendi…"];
export const ESPERA_FILLER_MS = 700; // só toca se a 1ª frase não chegou até aqui
export const PROBABILIDADE_FILLER = 0.5; // no máximo ~metade dos turnos

/**
 * Sorteia um filler entre os `prontos` (nunca o `ultimo`) ou devolve null: sem sorte
 * (probabilidade 0,5) ou sem candidato. Pura, para teste.
 */
export function sortear(prontos, ultimo, aleatorio = Math.random) {
    if (aleatorio() >= PROBABILIDADE_FILLER) return null;
    const candidatos = prontos.filter((t) => t !== ultimo);
    if (!candidatos.length) return null;
    return candidatos[Math.floor(aleatorio() * candidatos.length)];
}

/** O backend marca `risco` no evento `pensando`: só toca filler quando é "nenhum" (ou ausente). */
export function fillerPermitido(pensando) {
    const risco = pensando?.risco;
    return risco === undefined || risco === null || risco === "nenhum";
}

/**
 * Cache dos áudios de filler ("Hmm…"), gerados na abertura da entrevista com o tom da
 * persona. Falhas de TTS são ignoradas (o filler simplesmente não existe).
 */
export function useFillers() {
    const blobsRef = useRef(new Map()); // texto -> Blob (só os que já chegaram)
    const ultimoRef = useRef(null);
    const preparadoRef = useRef(false);

    const preparar = useCallback((tom, sessionId) => {
        preparadoRef.current = true;
        blobsRef.current = new Map();
        FRASES_FILLER.forEach((texto) => {
            api.synthesizeSpeech(texto, tom, sessionId)
                .then((blob) => blobsRef.current.set(texto, blob))
                .catch(() => {});
        });
    }, []);

    const sortearPronto = useCallback((aleatorio = Math.random) => {
        const texto = sortear([...blobsRef.current.keys()], ultimoRef.current, aleatorio);
        if (!texto) return null;
        ultimoRef.current = texto;
        return { texto, blob: blobsRef.current.get(texto) };
    }, []);

    return { preparar, sortear: sortearPronto, preparadoRef };
}
