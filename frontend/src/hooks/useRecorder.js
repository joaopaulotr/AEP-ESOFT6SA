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

    const recorderRef = useRef(null);
    const streamRef = useRef(null);
    const chunksRef = useRef([]);
    const canceladoRef = useRef(false);
    const montadoRef = useRef(true);

    const onRecordedRef = useRef(onRecorded);
    onRecordedRef.current = onRecorded;

    const liberar = useCallback(() => {
        const recorder = recorderRef.current;
        if (recorder && recorder.state !== "inactive") {
            canceladoRef.current = true; // descarta o que foi gravado
            recorder.stop();
        }
        recorderRef.current = null;
        streamRef.current?.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
        if (montadoRef.current) {
            setStream(null);
            setGravando(false);
        }
    }, []);

    const abrirMicrofone = useCallback(async () => {
        if (streamRef.current) return streamRef.current;
        const s = await navigator.mediaDevices.getUserMedia(RESTRICOES_MIC);
        if (!montadoRef.current) {
            s.getTracks().forEach((t) => t.stop());
            throw new Error("tela fechada");
        }
        streamRef.current = s;
        setEcoCancelado(s.getAudioTracks()[0]?.getSettings?.().echoCancellation === true);
        setStream(s);
        return s;
    }, []);

    const stop = useCallback(() => {
        const recorder = recorderRef.current;
        if (recorder && recorder.state !== "inactive") recorder.stop();
        setGravando(false);
    }, []);

    const start = useCallback(async () => {
        if (recorderRef.current) return;
        const s = await abrirMicrofone();
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
            const blob = new Blob(chunksRef.current, { type: "audio/webm" });
            onRecordedRef.current?.(blob);
        };

        recorder.start();
        recorderRef.current = recorder;
        setGravando(true);
    }, [abrirMicrofone]);

    const bargeInPossivel = ecoCancelado && !!stream;
    const modo = gravando ? "gravacao" : bargeInAtivo && bargeInPossivel ? "barge" : "ocioso";
    const { nivelRef } = useVoiceActivity({
        stream,
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
