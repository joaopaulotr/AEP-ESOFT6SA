import { useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import { agora, atrasoDePensar } from "../utils/tempo";
import { useAudioPlayer } from "./useAudioPlayer";
import { useTurnStream } from "./useTurnStream";
import { useFillers, ESPERA_FILLER_MS } from "./useFillers";
import { useTypewriter } from "./useTypewriter";
import { E2E } from "../utils/e2e";


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
    const [progresso, setProgresso] = useState({ ordem: 0, total: 0, acao: null });
    const [pendente, setPendente] = useState(null); // transcrição aguardando confirmação: { texto, editar? }
    const [encerrando, setEncerrando] = useState(false); // a fala atual é a última (encerramento/acolhimento)
    const [legenda, setLegenda] = useState(""); // frase da IA que está tocando agora

    const player = useAudioPlayer();
    const stream = useTurnStream();
    const fillers = useFillers();
    const digitador = useTypewriter(); // modo texto: revela a fala da IA no ritmo de digitação
    const [anuncio, setAnuncio] = useState(""); // última frase da IA pronta, para leitores de tela (1 vez por frase)
    const instantaneoRef = useRef(false); // trocou para voz no meio da revelação: o resto aparece de uma vez

    const sessionIdRef = useRef(null);
    const processandoRef = useRef(false);
    const iniciadoRef = useRef(false);
    const timersRef = useRef([]);
    const respostasRef = useRef(0);
    const montadoRef = useRef(true); // nada é agendado nem navega depois de desmontar
    const tomRef = useRef(undefined); // tom da persona, usado na voz
    const turnoPromiseRef = useRef(null); // turno em andamento (stream + áudio)
    const encerrandoRef = useRef(false); // "Concluir" clicado ou sessão já finalizada: sem novos turnos, sem erro falso
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
            if (vozRef.current) fillers.preparar(tomRef.current);
        } catch {
            // Sem o tom a voz usa o padrão do servidor.
        }
    }

    async function concluirFala(terminou) {
        await player.aguardarFila();
        if (!montadoRef.current) return;
        setLegenda("");
        if (terminou) {
            encerrandoRef.current = true;
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
        setAnuncio(fala);
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
        if (vozRef.current) fillers.preparar(tomRef.current);
        const turnos = sessao.conversation || [];
        respostasRef.current = turnos.filter((t) => t.role === "participant").length;
        setTranscricao(turnos.map((t) => ({ quem: t.role === "participant" ? "voce" : "ia", texto: t.text, hora: "" })));
        const ultima = [...turnos].reverse().find((t) => t.role === "interviewer");
        if (ultima) setPerguntaAtual(ultima.text);
        setIndiceAtual(sessao.current_index || 0);
        setProgresso({ ordem: (sessao.current_index || 0) + 1, total: det.script?.perguntas?.length || 0, acao: null });
        if (sessao.finished) {
            encerrandoRef.current = true;
            setEncerrando(true);
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
            setProgresso({ ordem: 1, total: data.perguntas_total || 0, acao: null });
            sessionIdRef.current = data.session_id;
            setSessionId(data.session_id);
            await carregarTom(data.session_id); // o tom vale também se a pessoa trocar para voz depois
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
        const naoAntesDe = Date.now() + (E2E ? 0 : atrasoDePensar(msg.length)); // a 1ª frase não toca antes disso
        let fim = null;
        let detalheErro = "";
        let falhou = false;
        let encerrado = false; // turno acabou (fim/erro/exceção): nenhum filler tardio
        let timerFiller = null;
        // Modo texto: cada frase entra numa cadeia que a revela em ordem (a 1ª só após o atraso de pensar).
        let cadeia = Promise.resolve();
        let cancelado = false;
        let primeira = true;
        const revelarFrase = (t) => {
            const depoisDe = primeira ? naoAntesDe : undefined;
            primeira = false;
            cadeia = cadeia.then(async () => {
                if (cancelado || !montadoRef.current) return;
                await digitador.revelar(t, { depoisDe, instantaneo: E2E || instantaneoRef.current });
                if (!cancelado && montadoRef.current) setAnuncio(t);
            });
        };
        if (!vozAtiva) digitador.novoTurno();
        try {
            await stream.enviar(id, msg, {
                onPensando: () => {
                    if (!vozAtiva || E2E) return;
                    // Demorou: talvez um "Hmm, entendi…". Entra na mesma fila, então a 1ª frase
                    // só começa depois que ele terminar (nunca sobrepõe).
                    timerFiller = setTimeout(() => {
                        if (encerrado || !montadoRef.current || frases.length || interrompidoRef.current) return;
                        const filler = fillers.sortear();
                        if (!filler) return;
                        player.enfileirar(filler.blob, { aoIniciar: () => setLegenda(filler.texto) });
                    }, ESPERA_FILLER_MS);
                    timersRef.current.push(timerFiller);
                },
                onFrase: ({ texto, finalizada: ultima }) => {
                    if (ultima) {
                        // Despedida/acolhimento: ninguém interrompe, já desde a 1ª frase.
                        encerrandoRef.current = true;
                        setEncerrando(true);
                    }
                    frases.push(texto);
                    if (!vozAtiva) revelarFrase(texto);
                    if (!vozAtiva || interrompidoRef.current) return;
                    falarFrase(texto, {
                        naoAntesDe: frases.length === 1 ? naoAntesDe : undefined,
                        aoIniciar: () => setProcessando(false),
                    });
                },
                onFim: (dados) => {
                    fim = dados;
                    encerrado = true;
                    clearTimeout(timerFiller);
                    if (dados?.finalizada) {
                        // Mensagem final (encerramento/acolhimento): ninguém interrompe.
                        encerrandoRef.current = true;
                        setEncerrando(true);
                    }
                },
                onErro: (dados) => {
                    encerrado = true;
                    clearTimeout(timerFiller);
                    falhou = true;
                    detalheErro = dados?.detail || "";
                },
            });
        } catch {
            falhou = true;
        } finally {
            encerrado = true;
            clearTimeout(timerFiller);
        }
        if (!montadoRef.current) return { erro: "", silencioso: true };
        if (!fim || falhou) {
            cancelado = true;
            digitador.parar();
            digitador.limpar();
            player.stop();
            setLegenda("");
            // "Concluir" (ou sair) aborta o stream de propósito: não é erro para mostrar.
            return { erro: detalheErro, silencioso: encerrandoRef.current && !detalheErro };
        }
        if (vozAtiva && !frases.length && !interrompidoRef.current) {
            falarFrase(fim.fala, { naoAntesDe, aoIniciar: () => setProcessando(false) });
        }
        if (!vozAtiva) {
            if (!frases.length) revelarFrase(fim.fala);
            await cadeia;
            if (!montadoRef.current) return { erro: "", silencioso: true };
        }
        return { fim };
    }

    async function enviarResposta(conteudo) {
        const msg = (conteudo ?? "").trim();
        if (!msg || !sessionIdRef.current || encerrandoRef.current) return false;
        if (turnoPromiseRef.current) await turnoPromiseRef.current; // barge-in: espera o turno anterior fechar
        if (!montadoRef.current || processandoRef.current || encerrandoRef.current) return false;

        interrompidoRef.current = false;
        instantaneoRef.current = false;
        // Começou em texto e passou para voz: prepara os fillers agora (valem do próximo turno).
        if (vozRef.current && !fillers.preparadoRef.current) fillers.preparar(tomRef.current);
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
                setProgresso((p) => ({
                    ordem: fim.pergunta_ordem || p.ordem,
                    total: fim.perguntas_total || p.total,
                    acao: fim.acao || null,
                }));
                adicionarMensagem("ia", fim.fala);
                digitador.limpar(); // a bolha em construção vira a mensagem definitiva
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
        setTurno("voce");
        if (!r.silencioso) falhar(r.erro || "Não consegui enviar sua resposta. Tente de novo.");
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
        if (!montadoRef.current || !texto?.trim()) return;
        // Voz: mostra o que foi entendido por 3 s (corrigível) antes de enviar.
        setPendente({ texto: texto.trim() });
    }

    /** Envia a transcrição confirmada (ou corrigida). */
    async function confirmarTranscricao(texto) {
        setPendente(null);
        const ok = await enviarResposta(texto);
        // Falhou (rede/erro do stream): devolve o texto já transcrito, aberto para edição, para
        // a pessoa reenviar sem falar tudo de novo.
        if (ok === false && montadoRef.current && !encerrandoRef.current) {
            setPendente({ texto: texto.trim(), editar: true });
        }
    }

    async function concluir() {
        const respostas = respostasRef.current;
        const aviso = respostas === 0
            ? "Você ainda não respondeu nada. Encerrar mesmo assim?"
            : "Encerrar a entrevista agora?";
        if (!window.confirm(aviso)) return;
        encerrandoRef.current = true;
        setPendente(null);
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

    // Passou para voz no meio da revelação: termina o texto na hora (sem timers pendentes).
    useEffect(() => {
        if (voz) {
            instantaneoRef.current = true;
            digitador.concluirAgora();
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reage só à troca para voz; `digitador` muda a cada render e reexecutaria o efeito
    }, [voz]);

    useEffect(() => {
        montadoRef.current = true;
        return () => {
            montadoRef.current = false;
            // eslint-disable-next-line react-hooks/exhaustive-deps -- queremos os timers vigentes na desmontagem, não os do momento do efeito
            timersRef.current.forEach(clearTimeout);
        };
    }, []);

    useEffect(() => {
        if (iniciadoRef.current) return;
        iniciadoRef.current = true;
        iniciar();
        // eslint-disable-next-line react-hooks/exhaustive-deps -- inicia a entrevista uma única vez ao montar (guardado por iniciadoRef)
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
        digitado: digitador.texto,
        anuncio,
        encerrando,
        audioReproduzindo: player.tocando,
        progresso,
        pendente,
        confirmarTranscricao,
        descartarPendente: () => setPendente(null),
        tentarDeNovo: iniciar,
        audioTocando: player.ocupado,
        pararAudio: interromper,
        falarAviso,
        enviarResposta,
        enviarAudio,
        concluir,
    };
}
