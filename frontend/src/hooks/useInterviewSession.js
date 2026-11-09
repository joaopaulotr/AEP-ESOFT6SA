import { useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import { agora } from "../utils/tempo";
import { useAudioPlayer } from "./useAudioPlayer";


export function useInterviewSession({ scriptId, onFinished } = {}) {
    const [sessionId, setSessionId] = useState(null);
    const [perguntaAtual, setPerguntaAtual] = useState("");
    const [indiceAtual, setIndiceAtual] = useState(0);
    const [turno, setTurno] = useState("interviewer"); // "interviewer" | "voce"
    const [processando, setProcessandoState] = useState(false);
    const [finalizada, setFinalizada] = useState(false);
    const [transcricao, setTranscricao] = useState([]);
    const [erro, setErro] = useState(null); 
    const [tituloRoteiro, setTituloRoteiro] = useState("");

    const player = useAudioPlayer();

   
    const sessionIdRef = useRef(null);
    const processandoRef = useRef(false);
    const iniciadoRef = useRef(false);
    const onFinishedRef = useRef(onFinished);
    onFinishedRef.current = onFinished;

    function setProcessando(valor) {
        processandoRef.current = valor;
        setProcessandoState(valor);
    }

    function falhar(mensagem) {
        setErro({ mensagem });
    }

    function adicionarMensagem(quem, texto) {
        setTranscricao((prev) => [...prev, { quem, texto, hora: agora() }]);
    }

    async function falar(fala) {
        try {
            const audio = await api.synthesizeSpeech(fala);
            await player.play(audio);
        } catch {
            // Sem voz, a entrevista continua pelo texto.
        }
    }

    async function apresentarFala(fala, indice, terminou) {
        setPerguntaAtual(fala);
        if (typeof indice === "number") setIndiceAtual(indice);
        adicionarMensagem("ia", fala);
        setTurno("interviewer");

        await falar(fala);

        if (terminou) {
            setFinalizada(true);
            setTimeout(() => onFinishedRef.current?.(sessionIdRef.current), 1200);
        } else {
            setTurno("voce");
        }
    }

    async function iniciar() {
        try {
            const data = await api.createSession({ scriptId });
            setTituloRoteiro(data.titulo || "");
            sessionIdRef.current = data.session_id;
            setSessionId(data.session_id);
            await apresentarFala(data.pergunta, 0, false);
        } catch (e) {
            falhar(e?.detail || "Não consegui iniciar a entrevista. O backend está no ar?");
        }
    }

    async function enviarResposta(conteudo) {
        const msg = (conteudo ?? "").trim();
        if (!msg || !sessionIdRef.current || processandoRef.current) return;

        adicionarMensagem("voce", msg);
        setProcessando(true);
        setTurno("interviewer");

        try {
            const data = await api.sendTurn(sessionIdRef.current, msg);
            setProcessando(false);
            await apresentarFala(data.fala, data.indice_atual, data.finalizada);
        } catch {
            setProcessando(false);
            falhar("Erro ao enviar a resposta.");
            setTurno("voce");
        }
    }

    async function enviarAudio(blob) {
        setProcessando(true);
        let texto;
        try {
            ({ texto } = await api.transcribeAudio(blob));
        } catch {
            setProcessando(false);
            falhar("Falha ao transcrever o áudio.");
            return;
        }
        setProcessando(false);
        await enviarResposta(texto);
    }

    async function concluir() {
        player.stop();
        const id = sessionIdRef.current;
        if (id) {
            try {
                await api.finishSession(id);
            } catch {
                // Mesmo com erro, leva para o feedback.
            }
        }
        onFinishedRef.current?.(id);
    }

    useEffect(() => {
        if (iniciadoRef.current) return; 
        iniciadoRef.current = true;
        iniciar();
        
    }, []);

    return {
        sessionId,
        tituloRoteiro,
        perguntaAtual,
        indiceAtual,
        turno,
        processando,
        finalizada,
        transcricao,
        erro,
        audioTocando: player.tocando, 
        enviarResposta,
        enviarAudio,
        concluir,
    };
}
