import { useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import { agora } from "../utils/tempo";
import { useAudioPlayer } from "./useAudioPlayer";
import { useTurnStream } from "./useTurnStream";


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
    const [legenda, setLegenda] = useState(""); // frase da IA que está tocando agora

    const player = useAudioPlayer();
    const stream = useTurnStream();

    const sessionIdRef = useRef(null);
    const processandoRef = useRef(false);
    const iniciadoRef = useRef(false);
    const timersRef = useRef([]);
    const respostasRef = useRef(0);
    const montadoRef = useRef(true); // nada é agendado nem navega depois de desmontar
    const tomRef = useRef(undefined); // tom da persona, usado na voz
    const turnoPromiseRef = useRef(null); // turno em andamento (stream + áudio)
    const interrompidoRef = useRef(false); // barge-in: as frases que ainda chegam não tocam
    const vozRef = useRef(voz);
    vozRef.current = voz;
    const ocupadoRef = useRef(false);
    ocupadoRef.current = player.ocupado;
    const onFinishedRef = useRef(onFinished);
    onFinishedRef.current = onFinished;

    function setProcessando(valor) {
        processandoRef.current = valor;
        setProcessandoState(valor);
    }

    function agendar(fn, ms) {
        if (!montadoRef.current) return;
        timersRef.current.push(
            setTimeout(() => {
                if (montadoRef.current) fn();
            }, ms)
        );
    }

    function falhar(mensagem) {
        setErro({ mensagem });
    }

    function adicionarMensagem(quem, texto) {
        if (quem === "voce") respostasRef.current += 1;
        setTranscricao((prev) => [...prev, { quem, texto, hora: agora() }]);
    }

    // Falha na síntese (null) = a frase segue só pela legenda.
    const sintetizar = (texto) => api.synthesizeSpeech(texto, tomRef.current).catch(() => null);

    /** Enfileira uma frase na fala; a legenda acompanha o áudio. */
    function falarFrase(texto, { aoIniciar, naoAntesDe } = {}) {
        if (!vozRef.current) return Promise.resolve();
        return player.enfileirar(sintetizar(texto), {
            naoAntesDe,
            aoIniciar: () => {
                setLegenda(texto);
                aoIniciar?.();
            },
        });
    }

    /** Frase avulsa (incentivo ao silêncio): só fala se a IA não estiver tocando nada. */
    function falarAviso(texto) {
        if (!vozRef.current || ocupadoRef.current || processandoRef.current) return;
        falarFrase(texto);
    }

    async function carregarTom(id) {
        try {
            const det = await api.getSessionDetails(id);
            tomRef.current = det.script?.persona?.tom;
        } catch {
            // Sem o tom a voz usa o padrão do servidor.
        }
    }

    async function concluirFala(terminou) {
        await player.aguardarFila();
        if (!montadoRef.current) return;
        setLegenda("");
        if (terminou) {
            setFinalizada(true);
            agendar(() => onFinishedRef.current?.(sessionIdRef.current), 1200);
        } else {
            setTurno("voce");
        }
    }

    async function apresentarFala(fala, indice, terminou) {
        setPerguntaAtual(fala);
        if (typeof indice === "number") setIndiceAtual(indice);
        adicionarMensagem("ia", fala);
        setTurno("interviewer");
        falarFrase(fala);
        await concluirFala(terminou);
    }

    async function retomar(id) {
        const det = await api.getSessionDetails(id);
        const sessao = det.session;
        sessionIdRef.current = id;
        setSessionId(id);
        setTituloRoteiro(det.script?.titulo || "");
        tomRef.current = det.script?.persona?.tom;
        const turnos = sessao.conversation || [];
        respostasRef.current = turnos.filter((t) => t.role === "participant").length;
        setTranscricao(turnos.map((t) => ({ quem: t.role === "participant" ? "voce" : "ia", texto: t.text, hora: "" })));
        const ultima = [...turnos].reverse().find((t) => t.role === "interviewer");
        if (ultima) setPerguntaAtual(ultima.text);
        setIndiceAtual(sessao.current_index || 0);
        if (sessao.finished) {
            setFinalizada(true);
            setTurno("interviewer");
            agendar(() => onFinishedRef.current?.(id), 300);
        } else {
            setTurno("voce");
            // Sessão recém-criada (nenhuma resposta ainda): fala a primeira pergunta.
            if (respostasRef.current === 0 && ultima) falarFrase(ultima.text);
        }
    }

    async function iniciar() {
        setErroInicio("");
        try {
            if (existente?.sessionId) {
                // Sempre busca a sessão: location.state sobrevive ao recarregar a página.
                await retomar(existente.sessionId);
                return;
            }
            const data = await api.createSession({ scriptId });
            setTituloRoteiro(data.titulo || "");
            sessionIdRef.current = data.session_id;
            setSessionId(data.session_id);
            if (vozRef.current) await carregarTom(data.session_id);
            await apresentarFala(data.pergunta, 0, false);
        } catch (e) {
            setErroInicio(e?.detail || "Não consegui iniciar a entrevista. O servidor está no ar?");
        }
    }

    /** Barge-in / sair do modo voz: corta a fala da IA; o que ainda chegar do turno não toca. */
    function interromper() {
        interrompidoRef.current = true;
        player.stop();
        setLegenda("");
        if (processandoRef.current) setProcessando(false);
    }

    /**
     * Lê o turno em streaming. Resolve com {fim} ou {erro}. Em modo voz cada frase vai para a
     * fila de áudio assim que chega (TTS em paralelo, toca em ordem).
     */
    async function lerTurno(id, msg) {
        const vozAtiva = vozRef.current;
        const frases = [];
        let fim = null;
        let detalheErro = "";
        let falhou = false;
        try {
            await stream.enviar(id, msg, {
                onFrase: ({ texto }) => {
                    frases.push(texto);
                    if (!vozAtiva || interrompidoRef.current) return;
                    falarFrase(texto, { aoIniciar: () => setProcessando(false) });
                },
                onFim: (dados) => {
                    fim = dados;
                },
                onErro: (dados) => {
                    falhou = true;
                    detalheErro = dados?.detail || "";
                },
            });
        } catch {
            falhou = true;
        }
        if (!montadoRef.current) return { erro: "" };
        if (!fim || falhou) {
            player.stop();
            setLegenda("");
            return { erro: detalheErro };
        }
        if (vozAtiva && !frases.length && !interrompidoRef.current) {
            falarFrase(fim.fala, { aoIniciar: () => setProcessando(false) });
        }
        return { fim };
    }

    async function enviarResposta(conteudo) {
        const msg = (conteudo ?? "").trim();
        if (!msg || !sessionIdRef.current) return;
        if (turnoPromiseRef.current) await turnoPromiseRef.current; // barge-in: espera o turno anterior fechar
        if (!montadoRef.current || processandoRef.current) return;

        interrompidoRef.current = false;
        adicionarMensagem("voce", msg);
        const desfazer = () => {
            respostasRef.current = Math.max(0, respostasRef.current - 1);
            setTranscricao((prev) => prev.slice(0, -1));
        };
        setProcessando(true);
        setTurno("interviewer");
        setLegenda("");

        const fase1 = lerTurno(sessionIdRef.current, msg);
        turnoPromiseRef.current = fase1
            .then(async (r) => {
                if (!r.fim || !montadoRef.current) return;
                const { fim } = r;
                setProcessando(false);
                setPerguntaAtual(fim.fala);
                if (typeof fim.indice_atual === "number") setIndiceAtual(fim.indice_atual);
                adicionarMensagem("ia", fim.fala);
                await concluirFala(fim.finalizada);
            })
            .finally(() => {
                turnoPromiseRef.current = null;
            });

        const r = await fase1;
        if (!montadoRef.current) return false;
        if (r.fim) return true;
        desfazer();
        setProcessando(false);
        falhar(r.erro || "Não consegui enviar sua resposta. Tente de novo.");
        setTurno("voce");
        return false;
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
        stream.cancelar();
        player.stop();
        const id = sessionIdRef.current;
        if (id) {
            try {
                await api.finishSession(id);
            } catch {
                // Mesmo com erro, leva para o feedback.
            }
        }
        if (montadoRef.current) onFinishedRef.current?.(id, { respostas });
    }

    useEffect(() => {
        montadoRef.current = true;
        return () => {
            montadoRef.current = false;
            timersRef.current.forEach(clearTimeout);
        };
    }, []);

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
        legenda,
        tentarDeNovo: iniciar,
        audioTocando: player.ocupado,
        pararAudio: interromper,
        falarAviso,
        enviarResposta,
        enviarAudio,
        concluir,
    };
}
