import { useCallback, useEffect, useRef, useState } from "react";

export function useRecorder({ onRecorded } = {}) {
    const [gravando, setGravando] = useState(false);

    const recorderRef = useRef(null);
    const streamRef = useRef(null);
    const chunksRef = useRef([]);
    const canceladoRef = useRef(false);

    
    const onRecordedRef = useRef(onRecorded);
    onRecordedRef.current = onRecorded;

    const liberarMicrofone = useCallback(() => {
        streamRef.current?.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
    }, []);

    const start = useCallback(async () => {
        if (recorderRef.current) return;

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        streamRef.current = stream;

        const recorder = new MediaRecorder(stream);
        chunksRef.current = [];

        recorder.ondataavailable = (e) => {
            if (e.data.size > 0) chunksRef.current.push(e.data);
        };
        recorder.onstop = () => {
            liberarMicrofone();
            recorderRef.current = null;
            if (canceladoRef.current) return;
            const blob = new Blob(chunksRef.current, { type: "audio/webm" });
            onRecordedRef.current?.(blob);
        };

        recorder.start();
        recorderRef.current = recorder;
        setGravando(true);
    }, [liberarMicrofone]);

    const stop = useCallback(() => {
        recorderRef.current?.stop();
        setGravando(false);
    }, []);

    useEffect(() => {
        canceladoRef.current = false;
        return () => {
            canceladoRef.current = true;
            recorderRef.current?.stop();
            liberarMicrofone();
        };
    }, [liberarMicrofone]);

    return { gravando, start, stop };
}
