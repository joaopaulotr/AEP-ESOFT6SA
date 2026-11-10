import { useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import { agora } from "../utils/tempo";
import { useAudioPlayer } from "./useAudioPlayer";


/**
 * `existente`: { sessionId, perguntaInicial?, titulo? } quando a sessão já foi criada
 * (entrada pelo convite). Nesse caminho nunca cria sessão nova: sem `perguntaInicial`
 * (página recarregada), busca a sessão e retoma da última fala do entrevistador.
 * `voz`: false no modo texto (sem TTS). Pode mudar durante a entrevista.
 */
export function useInterviewSession({ scriptId, onFinished, existente, voz = true } = {}) {
    const [sessionId, setSessionId] = useState(null);
    const [perguntaAtual, setPerguntaAtual] = useState("");
    const [indiceAtual, setIndiceAtual] = useState(0);
    const [turno, setTurno] = useState("interviewer"); // "interviewer" | "voce"
    const [processando, setProcessandoState] = useState(false);
    const [finalizada, setFinalizada] = useState(false);
    const [transcricao, setTranscricao] = useState([]);
    const [erro, setErro] = useState(null); 
    const [erroInicio, setErroInicio] = useState("");
    const [tituloRoteiro, setTituloRoteiro] = useState("");

    const player = useAudioPlayer();

   
    const sessionIdRef = useRef(null);
    const processandoRef = useRef(false);
    const iniciadoRef = useRef(false);
    const respostasRef = useRef(0);
    const vozRef = useRef(voz);
    vozRef.current = voz;
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
        if (quem === "voce") respostasRef.current += 1;
        setTranscricao((prev) => [...prev, { quem, texto, hora: agora() }]);
    }

    async function falar(fala) {
        if (!vozRef.current) return;
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

    async function retomar(id) {
        const det = await api.getSessionDetails(id);
        const sessao = det.session;
        sessionIdRef.current = id;
        setSessionId(id);
        setTituloRoteiro(det.script?.titulo || "");
        const turnos = sessao.conversation || [];
        respostasRef.current = turnos.filter((t) => t.role === "participant").length;
        setTranscricao(turnos.map((t) => ({ quem: t.role === "participant" ? "voce" : "ia", texto: t.text, hora: "" })));
        const ultima = [...turnos].reverse().find((t) => t.role === "interviewer");
        if (ultima) setPerguntaAtual(ultima.text);
        setIndiceAtual(sessao.current_index || 0);
        if (sessao.finished) {
            setFinalizada(true);
            setTurno("interviewer");
            setTimeout(() => onFinishedRef.current?.(id), 300);
        } else {
            setTurno("voce");
        }
    }

    async function iniciar() {
        setErroInicio("");
        try {
            if (existente?.sessionId) {
                if (existente.perguntaInicial) {
                    sessionIdRef.current = existente.sessionId;
                    setSessionId(existente.sessionId);
                    setTituloRoteiro(existente.titulo || "");
                    await apresentarFala(existente.perguntaInicial, 0, false);
                } else {
                    await retomar(existente.sessionId);
                }
                return;
            }
            const data = await api.createSession({ scriptId });
            setTituloRoteiro(data.titulo || "");
            sessionIdRef.current = data.session_id;
            setSessionId(data.session_id);
            await apresentarFala(data.pergunta, 0, false);
        } catch (e) {
            setErroInicio(e?.detail || "Não consegui iniciar a entrevista. O servidor está no ar?");
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
        const respostas = respostasRef.current;
        const aviso = respostas === 0
            ? "Você ainda não respondeu nada. Encerrar mesmo assim?"
            : "Encerrar a entrevista agora?";
        if (!window.confirm(aviso)) return;
        player.stop();
        const id = sessionIdRef.current;
        if (id) {
            try {
                await api.finishSession(id);
            } catch {
                // Mesmo com erro, leva para o feedback.
            }
        }
        onFinishedRef.current?.(id, { respostas });
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
        erroInicio,
        tentarDeNovo: iniciar,
        audioTocando: player.tocando,
        pararAudio: player.stop,
        enviarResposta,
        enviarAudio,
        concluir,
    };
}
