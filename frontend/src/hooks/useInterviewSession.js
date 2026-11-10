import { useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import { agora, atrasoDePensar } from "../utils/tempo";
import { useAudioPlayer } from "./useAudioPlayer";
import { useTurnStream } from "./useTurnStream";
import { useFillers, ESPERA_FILLER_MS, fillerPermitido } from "./useFillers";
import { useTypewriter } from "./useTypewriter";
import { E2E } from "../utils/e2e";


const espera = (ms) => new Promise((r) => setTimeout(r, ms));
const TENTATIVAS_RECUPERAR = 3;
const INTERVALO_RECUPERAR_MS = E2E ? 300 : 1500;

/**
 * `existente`: { sessionId, slug } quando a sessão já foi criada (entrada pelo convite). Nesse
 * caminho nunca cria sessão nova: lê o estado pela rota pública do convite e retoma da última fala
 * do entrevistador. `voz`: false no modo texto (sem TTS). Pode mudar durante a entrevista.
 * `onFinished(sessionId, { acolhimento, respostas? })`: com acolhimento a tela não sai sozinha —
 * mostra o cartão do CVV e só segue quando a pessoa chama `continuar()`.
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
    const [acolhimento, setAcolhimento] = useState(false); // fala de acolhimento: mostra o CVV e não sai sozinha

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
    const interrompidoRef = useRef(false); // barge-in: as frases que ainda chegam não tocam (exceto a final)
    const acolhimentoRef = useRef(false);
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

    // Falha (ou 8 s sem resposta) na síntese (null) = a frase segue só pela legenda.
    const sintetizar = (texto) => api.synthesizeSpeech(texto, tomRef.current, sessionIdRef.current).catch(() => null);

    function marcarAcolhimento() {
        if (acolhimentoRef.current) return;
        acolhimentoRef.current = true;
        setAcolhimento(true);
    }

    /** Fim da entrevista: sem acolhimento segue sozinho; com acolhimento espera o "Continuar". */
    function finalizar(comAcolhimento, atrasoMs) {
        encerrandoRef.current = true;
        setEncerrando(true);
        setFinalizada(true);
        setTurno("interviewer");
        if (comAcolhimento || acolhimentoRef.current) {
            marcarAcolhimento();
            return;
        }
        agendar(() => onFinishedRef.current?.(sessionIdRef.current, { acolhimento: false }), atrasoMs);
    }

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

    /**
     * Frase avulsa (incentivo ao silêncio): só fala se a IA não estiver tocando nada. Ao terminar, a
     * legenda volta para a pergunta (o incentivo não fica no lugar dela).
     */
    function falarAviso(texto) {
        if (!vozRef.current || ocupadoRef.current || processandoRef.current) return;
        falarFrase(texto).then(() => {
            if (montadoRef.current) setLegenda((atual) => (atual === texto ? "" : atual));
        });
    }

    /**
     * Estado atual da sessão no servidor, no mesmo formato nos dois caminhos: convite (rota
     * pública, sem objetivos nem perfil) ou pesquisador (detalhes).
     */
    async function lerEstado(id) {
        if (existente?.slug) {
            const est = await api.getPublicSession(existente.slug, id);
            return {
                titulo: est.titulo || "",
                tom: est.persona?.tom,
                conversation: est.conversation || [],
                current_index: est.current_index || 0,
                perguntas_total: est.perguntas_total || 0,
                finished: !!est.finished,
                acolhimento: !!est.acolhimento,
            };
        }
        const det = await api.getSessionDetails(id);
        return {
            titulo: det.script?.titulo || "",
            tom: det.script?.persona?.tom,
            conversation: det.session?.conversation || [],
            current_index: det.session?.current_index || 0,
            perguntas_total: det.script?.perguntas?.length || 0,
            finished: !!det.session?.finished,
            acolhimento: !!det.session?.acolhimento,
        };
    }

    async function carregarTom(id) {
        try {
            const est = await lerEstado(id);
            tomRef.current = est.tom;
            if (vozRef.current) fillers.preparar(tomRef.current, id);
        } catch {
            // Sem o tom a voz usa o padrão do servidor.
        }
    }

    async function concluirFala(terminou, comAcolhimento = false) {
        await player.aguardarFila();
        if (!montadoRef.current) return;
        setLegenda("");
        if (terminou) finalizar(comAcolhimento, 1200);
        else setTurno("voce");
    }

    async function apresentarFala(fala, indice, terminou, comAcolhimento = false) {
        setPerguntaAtual(fala);
        if (typeof indice === "number") setIndiceAtual(indice);
        adicionarMensagem("ia", fala);
        setAnuncio(fala);
        setTurno("interviewer");
        if (terminou) {
            encerrandoRef.current = true;
            setEncerrando(true);
            if (comAcolhimento) marcarAcolhimento();
        }
        falarFrase(fala);
        await concluirFala(terminou, comAcolhimento);
    }

    async function retomar(id) {
        const est = await lerEstado(id);
        sessionIdRef.current = id;
        setSessionId(id);
        setTituloRoteiro(est.titulo);
        tomRef.current = est.tom;
        if (vozRef.current) fillers.preparar(tomRef.current, id);
        const turnos = est.conversation;
        respostasRef.current = turnos.filter((t) => t.role === "participant").length;
        setTranscricao(turnos.map((t) => ({ quem: t.role === "participant" ? "voce" : "ia", texto: t.text, hora: "" })));
        const ultima = [...turnos].reverse().find((t) => t.role === "interviewer");
        if (ultima) setPerguntaAtual(ultima.text);
        setIndiceAtual(est.current_index);
        setProgresso({ ordem: est.current_index + 1, total: est.perguntas_total, acao: null });
        if (est.finished) {
            finalizar(est.acolhimento, 300);
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
        let status = 0;
        let falhou = false;
        let acolheu = false;
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
                onPensando: (dados) => {
                    // Risco detectado (sofrimento/pedido de parar): nenhum "Hmm…" antes da resposta.
                    if (!vozAtiva || E2E || !fillerPermitido(dados)) return;
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
                onFrase: ({ texto, finalizada: ultima, acolhimento: acolhe }) => {
                    if (ultima) {
                        // Despedida/acolhimento: ninguém interrompe, já desde a 1ª frase.
                        encerrandoRef.current = true;
                        setEncerrando(true);
                    }
                    if (acolhe) {
                        acolheu = true;
                        marcarAcolhimento();
                    }
                    frases.push(texto);
                    if (!vozAtiva) revelarFrase(texto);
                    // A fala final (acolhimento/despedida) toca mesmo depois de um barge-in no filler.
                    if (!vozAtiva || (interrompidoRef.current && !ultima)) return;
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
                    if (dados?.acolhimento) {
                        acolheu = true;
                        marcarAcolhimento();
                    }
                },
                onErro: (dados) => {
                    encerrado = true;
                    clearTimeout(timerFiller);
                    falhou = true;
                    detalheErro = dados?.detail || "";
                },
            });
        } catch (e) {
            falhou = true;
            detalheErro = e?.detail || detalheErro;
            status = e?.status || 0;
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
            return { erro: detalheErro, status, silencioso: encerrandoRef.current && !detalheErro && status !== 409 };
        }
        if (acolheu) fim = { ...fim, acolhimento: true };
        if (vozAtiva && !frases.length && (!interrompidoRef.current || fim.finalizada)) {
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
                await concluirFala(fim.finalizada, !!fim.acolhimento);
            })
            .finally(() => {
                turnoPromiseRef.current = null;
            });

        const r = await fase1;
        if (!montadoRef.current) return false;
        if (r.fim) return true;
        if (!r.silencioso) {
            // O stream caiu sem `fim`: o servidor pode ter gravado o turno mesmo assim. Reenviar
            // duplicaria a resposta, então primeiro relê a sessão.
            const recuperado = await recuperarTurno(r.status === 409);
            if (!montadoRef.current) return false;
            if (recuperado === "ok") return true;
            if (recuperado === "travado") {
                setProcessando(false);
                falhar("Sua resposta foi recebida, mas a fala da entrevistadora não chegou. Recarregue a página para continuar.");
                return true; // não devolve o texto para reenvio: já está gravado
            }
        }
        desfazer();
        setProcessando(false);
        setTurno("voce");
        if (!r.silencioso) falhar(r.erro || "Não consegui enviar sua resposta. Tente de novo.");
        return false;
    }

    /**
     * Depois de uma queda do stream: "ok" se o servidor já tinha gravado a resposta (apresenta a fala
     * salva) ou se a sessão já estava encerrada (409); "naoGravada" se dá para reenviar; "travado" se
     * a resposta foi gravada mas a fala da entrevistadora ainda não apareceu.
     */
    async function recuperarTurno(conflito) {
        const id = sessionIdRef.current;
        let gravada = false;
        for (let i = 0; i < TENTATIVAS_RECUPERAR; i += 1) {
            if (i > 0) await espera(INTERVALO_RECUPERAR_MS);
            if (!montadoRef.current) return "naoGravada";
            let est;
            try {
                est = await lerEstado(id);
            } catch {
                continue;
            }
            if (!montadoRef.current) return "naoGravada";
            const turnos = est.conversation;
            const respostasServidor = turnos.filter((t) => t.role === "participant").length;
            const ultimo = turnos[turnos.length - 1];
            gravada = respostasServidor >= respostasRef.current;
            if (gravada && ultimo?.role === "interviewer") {
                setProcessando(false);
                digitador.limpar();
                setProgresso((p) => ({ ordem: est.current_index + 1, total: est.perguntas_total || p.total, acao: null }));
                await apresentarFala(ultimo.text, est.current_index, est.finished, est.acolhimento);
                return "ok";
            }
            if (est.finished) {
                setProcessando(false);
                finalizar(est.acolhimento, 300);
                return "ok";
            }
            if (!gravada && !conflito) return "naoGravada";
        }
        if (conflito) {
            setProcessando(false);
            finalizar(false, 300);
            return "ok";
        }
        return gravada ? "travado" : "naoGravada";
    }

    async function enviarAudio(blob) {
        setProcessando(true);
        let texto;
        try {
            ({ texto } = await api.transcribeAudio(blob, sessionIdRef.current));
        } catch {
            setProcessando(false);
            falhar("Falha ao transcrever o áudio.");
            return;
        }
        setProcessando(false);
        if (!montadoRef.current) return;
        if (!texto?.trim()) {
            falhar("Não consegui ouvir sua resposta. Tente falar de novo, mais perto do microfone.");
            return;
        }
        // Voz: mostra o que foi entendido por 8 s (corrigível) antes de enviar.
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
        if (encerrandoRef.current) return;
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
        if (montadoRef.current) onFinishedRef.current?.(id, { respostas, acolhimento: acolhimentoRef.current });
    }

    /** "Continuar" no cartão do CVV: só agora sai da tela. */
    function continuar() {
        onFinishedRef.current?.(sessionIdRef.current, { acolhimento: true });
    }

    /** Modo texto: mostra de uma vez o resto da fala que está sendo digitada. */
    function mostrarTudo() {
        instantaneoRef.current = true;
        digitador.concluirAgora();
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
        acolhimento,
        continuar,
        mostrarTudo,
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
