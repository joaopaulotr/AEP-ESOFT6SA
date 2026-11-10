import { useCallback, useEffect, useRef, useState } from "react";
import { useVoiceActivity } from "./useVoiceActivity";

const RESTRICOES_MIC = { audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } };

/**
 * Gravação por MediaRecorder + fim de fala automático (VAD). O botão manual continua valendo.
 * O microfone é aberto no primeiro `start()` (gesto do usuário) e fica aberto enquanto a tela
 * está no modo voz, para ouvir a interrupção da IA; `liberar()` e o desmonte fecham tudo.
 * `bargeInAtivo`: a IA está falando e o barge-in pode valer. Só vale se o navegador confirmar
 * `echoCancellation` na trilha (senão a IA se interromperia com a própria voz).
 */
export function useRecorder({ onRecorded, bargeInAtivo = false, aoBargeIn } = {}) {
    const [gravando, setGravando] = useState(false);
    const [stream, setStream] = useState(null);
    const [ecoCancelado, setEcoCancelado] = useState(false);
    const [contexto, setContexto] = useState(null);

    const recorderRef = useRef(null);
    const streamRef = useRef(null);
    const chunksRef = useRef([]);
    const canceladoRef = useRef(false);
    const montadoRef = useRef(true);
    const contextoRef = useRef(null);
    const ecoRef = useRef(false);
    const geracaoMicRef = useRef(0); // cada liberar() invalida um getUserMedia ainda pendente

    const onRecordedRef = useRef(onRecorded);
    onRecordedRef.current = onRecorded;

    // Fecha trilhas e AudioContext (sem descartar o que já foi gravado).
    const fecharMicrofone = useCallback(() => {
        streamRef.current?.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        contextoRef.current?.close?.().catch(() => {});
        contextoRef.current = null;
        if (montadoRef.current) {
            setStream(null);
            setContexto(null);
        }
    }, []);

    const liberar = useCallback(() => {
        geracaoMicRef.current += 1;
        const recorder = recorderRef.current;
        if (recorder && recorder.state !== "inactive") {
            canceladoRef.current = true; // descarta o que foi gravado
            recorder.stop();
        }
        recorderRef.current = null;
        fecharMicrofone();
        if (montadoRef.current) setGravando(false);
    }, [fecharMicrofone]);

    const abrirMicrofone = useCallback(async () => {
        if (streamRef.current) return streamRef.current;
        const geracao = geracaoMicRef.current;
        const s = await navigator.mediaDevices.getUserMedia(RESTRICOES_MIC);
        // Trocou para texto / saiu da tela enquanto a permissão era pedida: não deixa o mic aberto.
        if (!montadoRef.current || geracao !== geracaoMicRef.current) {
            s.getTracks().forEach((t) => t.stop());
            throw new Error("microfone liberado");
        }
        streamRef.current = s;
        ecoRef.current = s.getAudioTracks()[0]?.getSettings?.().echoCancellation === true;
        setEcoCancelado(ecoRef.current);
        setStream(s);
        setContexto(contextoRef.current);
        return s;
    }, []);

    const stop = useCallback(() => {
        const recorder = recorderRef.current;
        if (recorder && recorder.state !== "inactive") recorder.stop();
        setGravando(false);
    }, []);

    const start = useCallback(async () => {
        if (recorderRef.current) return;
        // O AudioContext nasce aqui, dentro do gesto do usuário (clique no microfone).
        if (!contextoRef.current) {
            const Ctx = window.AudioContext || window.webkitAudioContext;
            if (Ctx) {
                contextoRef.current = new Ctx();
                contextoRef.current.resume?.().catch(() => {});
            }
        }
        let s;
        try {
            s = await abrirMicrofone();
        } catch (e) {
            if (!streamRef.current) {
                contextoRef.current?.close?.().catch(() => {});
                contextoRef.current = null;
            }
            throw e;
        }
        if (recorderRef.current) return;

        const recorder = new MediaRecorder(s);
        chunksRef.current = [];
        canceladoRef.current = false;

        recorder.ondataavailable = (e) => {
            if (e.data.size > 0) chunksRef.current.push(e.data);
        };
        recorder.onstop = () => {
            if (recorderRef.current === recorder) recorderRef.current = null;
            if (canceladoRef.current) return;
            // Sem cancelamento de eco o barge-in não existe: não há motivo para manter o mic aberto.
            if (!ecoRef.current) fecharMicrofone();
            const blob = new Blob(chunksRef.current, { type: "audio/webm" });
            onRecordedRef.current?.(blob);
        };

        recorder.start();
        recorderRef.current = recorder;
        setGravando(true);
    }, [abrirMicrofone, fecharMicrofone]);

    const bargeInPossivel = ecoCancelado && !!stream;
    const modo = gravando ? "gravacao" : bargeInAtivo && bargeInPossivel ? "barge" : "ocioso";
    const { nivelRef } = useVoiceActivity({
        stream,
        contexto,
        modo,
        aoSilencio: stop,
        aoFalaContinua: () => aoBargeIn?.(),
    });

    useEffect(() => {
        montadoRef.current = true;
        return () => {
            montadoRef.current = false;
            liberar();
        };
    }, [liberar]);

    return { gravando, start, stop, liberar, nivelRef, microfoneAberto: !!stream, bargeInPossivel };
}
