import { useEffect, useRef, useState } from "react";
import { Navigate, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Mic, MicOff, Square, Send, Volume2, XCircle, Clock, PenLine } from "lucide-react";
import PublicLayout from "../components/PublicLayout";
import ChatComposer from "../components/ChatComposer";
import SideBar from "../components/SideBar";
import Avatar from "../components/Avatar";
import Waveform from "../components/Waveform";
import LiveCaption from "../components/LiveCaption";
import InterviewProgress from "../components/InterviewProgress";
import TranscriptConfirm from "../components/TranscriptConfirm";
import ThemeToggle from "../components/ThemeToggle";
import CvvAviso from "../components/CvvAviso";
import { api } from "../services/api";
import { lerSessaoPublica, guardarCanalPublico } from "../utils/sessaoPublica";
import { useInterviewSession } from "../hooks/useInterviewSession";
import { useRecorder } from "../hooks/useRecorder";
import { useElapsedTime } from "../hooks/useElapsedTime";
import { mmss } from "../utils/tempo";
import EstadoTela from "../components/EstadoTela";
import { ui, CSS as UI_CSS } from "../styles/ui";
import { style, CSS } from "./InterviewScreen.styles";
import { E2E } from "../utils/e2e";

const INTERVIEWER = "du";
const SILENCIO_INCENTIVO_MS = 12000;
const SO_LEITOR = { position: "absolute", width: 1, height: 1, margin: -1, padding: 0, overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap", border: 0 };
const INCENTIVO = "Pode ficar à vontade, sem pressa.";

/**
 * `publico`: rota `/e/:slug/entrevista` (participante do convite) - sem menu do pesquisador,
 * sessão já criada (id guardado no sessionStorage por slug, nunca na URL), termina na tela de
 * agradecimento.
 */
export default function InterviewScreen({ publico = false }) {
    const { slug } = useParams();
    const location = useLocation();
    // sessionStorage indisponível (modo privado restrito): o id segue no state da navegação.
    const [guardada] = useState(() =>
        publico ? lerSessaoPublica(slug) ?? (location.state?.sessionId ? location.state : null) : null,
    );
    if (publico && !guardada) return <Navigate to={`/e/${encodeURIComponent(slug || "")}`} replace />;
    return <Entrevista publico={publico} slug={slug} guardada={guardada} />;
}

function Entrevista({ publico, slug, guardada }) {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const scriptId = publico ? undefined : searchParams.get("roteiro") || undefined;
    const [existente] = useState(() => (guardada ? { sessionId: guardada.sessionId, slug } : undefined));
    const [modo, setModo] = useState(guardada?.canal === "texto" ? "texto" : "voz");
    const modoTexto = modo === "texto";
    const Shell = publico ? PublicLayout : SideBar;
    const [texto, setTexto] = useState("");
    const msgsRef = useRef(null);
    const segundos = useElapsedTime();

    const sessao = useInterviewSession({
        scriptId,
        existente,
        voz: !modoTexto,
        onFinished: (sessionId, extra) =>
            publico
                ? navigate(`/e/${encodeURIComponent(slug)}/obrigado`, { replace: true, state: { acolhimento: !!extra?.acolhimento } })
                : navigate("/feedback", { state: { sessionId, ...extra } }),
    });
    const [erroMic, setErroMic] = useState("");
    const { perguntaAtual, indiceAtual, turno, processando, finalizada, transcricao, erro, progresso, pendente } = sessao;

    const { pararAudio, falarAviso, descartarPendente } = sessao;
    const recorder = useRecorder({
        onRecorded: sessao.enviarAudio,
        // Barge-in: a pessoa começou a falar por cima da IA → corta o áudio e já grava.
        // só com um <audio> de fato tocando, e nunca na mensagem final (encerramento/acolhimento)
        bargeInAtivo: !modoTexto && sessao.audioReproduzindo && !sessao.encerrando && !finalizada,
        iaOcupada: sessao.audioTocando,
        aoBargeIn: () => {
            pararAudio();
            recorder.start().catch(() => {});
        },
    });

    // Ao trocar para texto (ou encerrar) o áudio para e o microfone é liberado.
    const { liberar: liberarMicrofone } = recorder;
    useEffect(() => {
        if (modoTexto) {
            pararAudio();
            descartarPendente();
            liberarMicrofone();
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- dispara só ao entrar no modo texto; as funções de áudio são recriadas a cada render
    }, [modoTexto]);
    useEffect(() => {
        if (finalizada) liberarMicrofone();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- dispara só ao finalizar; `liberarMicrofone` não precisa reiniciar o efeito
    }, [finalizada]);

    useEffect(() => {
        const el = msgsRef.current;
        if (el) el.scrollTop = el.scrollHeight;
    }, [transcricao, sessao.digitado]);

    // Incentivo: 12 s esperando a pessoa sem que ela fale -> uma vez por pergunta.
    const [incentivo, setIncentivo] = useState(false);
    const aguardando = turno === "voce" && !processando && !finalizada && !recorder.gravando && !pendente;
    const incentivadoRef = useRef(null); // pergunta (ordem) que já recebeu o incentivo
    const [digitou, setDigitou] = useState(0); // cada tecla no modo texto reinicia a espera
    const ordemAtual = progresso.ordem || indiceAtual + 1;
    useEffect(() => {
        setIncentivo(false);
    }, [ordemAtual]);
    useEffect(() => {
        if (E2E || !aguardando || incentivadoRef.current === ordemAtual) return undefined;
        const t = setTimeout(() => {
            incentivadoRef.current = ordemAtual; // uma vez por pergunta
            setIncentivo(true);
            falarAviso(INCENTIVO);
        }, SILENCIO_INCENTIVO_MS);
        return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `digitou` só reinicia a espera; `falarAviso` é recriada a cada render e não deve zerar o timer
    }, [aguardando, ordemAtual, digitou]);

    const podeResponder = turno === "voce" && !processando && !finalizada && !pendente;
    const ouvindo = recorder.gravando; // inclui a gravação iniciada por barge-in (turno ainda é da IA)
    const iaFalando = !modoTexto && turno === "interviewer" && !processando && !finalizada;
    const podeAlternar = !recorder.gravando && !processando && !finalizada && !sessao.encerrando && !!sessao.sessionId;
    const podeConcluir = !!sessao.sessionId && !sessao.encerrando && !finalizada;

    async function comecarGravacao() {
        if (!podeResponder) return;
        setErroMic("");
        try {
            await recorder.start();
        } catch {
            setErroMic("Não consegui acessar o microfone. Libere o microfone no navegador ou toque em “Prefiro escrever”.");
        }
    }

    function alternarModo() {
        const novo = modoTexto ? "voz" : "texto";
        setModo(novo);
        setErroMic("");
        if (publico && sessao.sessionId) {
            guardarCanalPublico(slug, novo);
            api.setPublicChannel(slug, sessao.sessionId, novo).catch(() => {}); // só estatística: falha não atrapalha
        }
    }

    function enviarTexto() {
        if (!podeResponder || !texto.trim()) return;
        sessao.enviarResposta(texto);
        setTexto("");
    }

    const estadoOnda = ouvindo ? "ouvindo" : processando ? "pensando" : sessao.audioTocando ? "falando" : "parado";
    // EV-80: a onda e o avatar seguem o microfone ao ouvir e a voz da IA ao falar.
    const nivelOnda = estadoOnda === "falando" ? sessao.nivelVozRef : recorder.nivelRef;
    const legendaTexto = processando ? "" : sessao.legenda || perguntaAtual;
    // Única região ao vivo do modo voz (montada desde o início): o que foi entendido, "pensando" e a fala.
    const anuncioVoz = pendente
        ? `Entendi assim: ${pendente.texto}. Envio automático em 8 segundos.`
        : processando
        ? "Pensando…"
        : incentivo && aguardando
        ? INCENTIVO
        : sessao.legenda;
    const anuncioTexto = processando && !sessao.digitado ? "Pensando…" : sessao.anuncio;

    const statusTexto = processando
        ? "PROCESSANDO…"
        : ouvindo
        ? "OUVINDO SUA RESPOSTA…"
        : iaFalando
        ? `${INTERVIEWER.toUpperCase()} ESTÁ FALANDO…`
        : finalizada
        ? "ENTREVISTA ENCERRADA"
        : "SUA VEZ DE RESPONDER";

    const alternar = (
        <button
            className="ui-btn"
            style={{ ...ui.btnSecundario, opacity: podeAlternar ? 1 : 0.5 }}
            disabled={!podeAlternar}
            aria-label={`${modoTexto ? "Prefiro falar" : "Prefiro escrever"}. Modo atual: ${modoTexto ? "escrever" : "falar"}`}
            onClick={alternarModo}
        >
            {modoTexto ? <Mic size={16} aria-hidden="true" /> : <PenLine size={16} aria-hidden="true" />}
            {modoTexto ? "Prefiro falar" : "Prefiro escrever"}
        </button>
    );

    if (sessao.erroInicio) {
        return (
            <Shell>
                <div style={ui.page}>
                    <style>{UI_CSS}</style>
                    <EstadoTela erro={sessao.erroInicio} onRetry={sessao.tentarDeNovo} />
                    <button className="ui-btn" style={ui.voltar} onClick={() => navigate(publico ? `/e/${encodeURIComponent(slug)}` : "/entrevistas")}>
                        {publico ? "Voltar ao convite" : "Escolher outra entrevista"}
                    </button>
                </div>
            </Shell>
        );
    }

    return (
        <Shell>
            <div style={style.root}>
                <style>{CSS}</style>

                <header style={style.topbar}>
                    <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
                        <span style={style.recTag}><span className="rec-dot" /> ENTREVISTA EM ANDAMENTO</span>
                        {sessao.tituloRoteiro && <span style={style.roteiroTitulo}>{sessao.tituloRoteiro}</span>}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <span style={style.timer}><Clock size={15} /> {mmss(segundos)}</span>
                        {!publico && <ThemeToggle />}
                        {sessao.sessionId && (
                            <button style={{ ...style.concluirBtn, opacity: podeConcluir ? 1 : 0.5 }} onClick={sessao.concluir} disabled={!podeConcluir}>
                                <XCircle size={17} aria-hidden="true" /> Concluir
                            </button>
                        )}
                    </div>
                </header>

                {sessao.acolhimento && (
                    <CvvAviso focar aoContinuar={sessao.continuar} podeContinuar={finalizada} />
                )}

                <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "flex-end", alignItems: "center", gap: 10, marginBottom: 14 }}>
                    {!modoTexto && recorder.microfoneAberto && !recorder.gravando && (
                        <>
                            <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13.5, fontWeight: 600, color: "var(--color-status)" }}>
                                <Mic size={15} aria-hidden="true" /> Microfone ligado
                            </span>
                            <button className="ui-btn" style={ui.btnSecundario} onClick={recorder.liberar}>
                                <MicOff size={16} aria-hidden="true" /> Desligar microfone
                            </button>
                        </>
                    )}
                    {alternar}
                </div>

                {sessao.recuperando && (
                    <p role="status" style={{ margin: "0 0 12px", fontSize: 14.5, fontWeight: 600, color: "var(--color-status)" }}>
                        Ainda estou processando sua resposta…
                    </p>
                )}
                {(erroMic || erro) && (
                    <p role="alert" style={{ margin: "0 0 12px", padding: "10px 12px", borderRadius: 12, border: "1px solid var(--color-error)", color: "var(--color-error)", fontSize: 14.5 }}>
                        {erroMic || erro.mensagem}
                    </p>
                )}

                {modoTexto ? (
                    <div style={{ ...style.colRight, maxWidth: 760, margin: "0 auto" }}>
                        <div style={{ padding: "12px 14px 0" }}><InterviewProgress {...progresso} /></div>
                        <div
                            style={{ ...style.msgs, maxHeight: "60vh" }}
                            ref={msgsRef}
                            role="log"
                            aria-live="off"
                            aria-label="Conversa da entrevista"
                        >
                            {transcricao.length === 0 && <p style={ui.meta}>Conectando à entrevista…</p>}
                            {transcricao.map((m, i) => (
                                <div key={i} style={{ alignSelf: m.quem === "ia" ? "flex-start" : "flex-end", maxWidth: "88%" }}>
                                    <div style={style.msgMeta}>
                                        {m.quem === "ia" ? INTERVIEWER : "Você"}{m.hora ? ` · ${m.hora}` : ""}
                                    </div>
                                    <div style={{ ...style.bubble, ...(m.quem === "voce" ? style.bubbleMe : {}) }}>{m.texto}</div>
                                </div>
                            ))}
                            {processando && (
                                <div style={{ alignSelf: "flex-start", maxWidth: "88%" }} aria-hidden="true">
                                    <div style={style.msgMeta}>{INTERVIEWER}</div>
                                    {sessao.digitado ? (
                                        <div style={style.bubble}>{sessao.digitado}</div>
                                    ) : (
                                        <div style={{ ...style.bubble, fontStyle: "italic", color: "var(--color-text-muted)" }}>digitando…</div>
                                    )}
                                </div>
                            )}
                        </div>
                        {processando && sessao.digitado && (
                            <div style={{ padding: "0 14px" }}>
                                <button className="ui-btn" style={ui.btnSecundario} onClick={sessao.mostrarTudo}>Mostrar tudo</button>
                            </div>
                        )}
                        {/* Única região ao vivo do modo texto: "Pensando…" e a frase pronta (não cada caractere). */}
                        <div style={SO_LEITOR} role="status" aria-live="polite" aria-label="Fala do entrevistador">{anuncioTexto}</div>
                        {incentivo && aguardando && <p style={{ ...style.incentivo, padding: "0 14px" }}>{INCENTIVO}</p>}
                        <ChatComposer
                            desabilitado={!sessao.sessionId || finalizada || turno !== "voce"}
                            enviando={processando}
                            onSend={sessao.enviarResposta}
                            aoDigitar={() => setDigitou((n) => n + 1)}
                        />
                    </div>
                ) : (
                <div style={style.row}>
                    <div style={style.colLeft}>
                        <div style={style.aiPanel}>
                            <div style={style.panelHead}>
                                <InterviewProgress {...progresso} />
                                <span style={style.voiceChip}><Volume2 size={14} /> Voz: Ativada</span>
                            </div>

                            <div style={style.avatarWrap}>
                                <Avatar size={128} estado={estadoOnda} nivelRef={nivelOnda} />
                            </div>

                            <p style={style.status}>{statusTexto}</p>
                            {incentivo && aguardando && <p style={style.incentivo}>{INCENTIVO}</p>}

                            <Waveform estado={estadoOnda} nivelRef={nivelOnda} />

                            <div style={style.questionCard}>
                                <LiveCaption texto={legendaTexto} vazio={processando ? "…" : undefined} />
                            </div>
                            <div style={SO_LEITOR} role="status" aria-live="polite" aria-atomic="true" aria-label="Fala do entrevistador">{anuncioVoz}</div>
                        </div>


                        {pendente && <TranscriptConfirm key={`${pendente.texto}|${pendente.editar ? "e" : "a"}`} texto={pendente.texto} editarInicial={!!pendente.editar} onEnviar={sessao.confirmarTranscricao} />}

                        <div style={style.bottomBar}>
                            <div style={{ flex: 1 }}>
                                <p style={{ margin: 0, fontSize: 12.5, color: "var(--color-text-muted)" }}>Status</p>
                                <p style={{ margin: "2px 0 0", fontSize: 14, fontWeight: 700, color: "var(--color-status)" }}>
                                    {processando ? "Processando…" : podeResponder || ouvindo ? "Pronta para ouvir" : "Aguarde…"}
                                </p>
                            </div>
                            <button
                                className="mic-btn"
                                aria-label={recorder.gravando ? "Parar e enviar resposta" : "Falar ao microfone"}
                                style={{ ...style.micBtn, opacity: podeResponder || ouvindo ? 1 : 0.5, cursor: podeResponder || ouvindo ? "pointer" : "default" }}
                                disabled={!podeResponder && !ouvindo}
                                onClick={recorder.gravando ? recorder.stop : comecarGravacao}
                            >
                                {recorder.gravando ? <Square size={18} fill="currentColor" /> : <Mic size={18} />}
                                <span style={{ lineHeight: 1.1 }}>{recorder.gravando ? "Enviar resposta" : "Falar ao Microfone"}</span>
                            </button>
                        </div>
                    </div>

                    <div style={style.colRight}>
                        <div style={style.transcricao}>
                            <span style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 700, color: "var(--color-text)", fontSize: 15 }}>
                                Transcrição ao Vivo
                            </span>
                            <span style={style.pill}>Tempo Real</span>
                        </div>

                        {/* Sem aria-live: no modo voz a fala da IA já é anunciada pela legenda (uma só região ao vivo). */}
                        <div style={style.msgs} ref={msgsRef} role="log" aria-live="off" aria-label="Transcrição da entrevista">
                            {transcricao.map((m, i) => (
                                <div key={i} style={{ alignSelf: m.quem === "ia" ? "flex-start" : "flex-end", maxWidth: "88%" }}>
                                    <div style={style.msgMeta}>
                                        {m.quem === "ia" ? `${INTERVIEWER} ` : "Você"} · {m.hora}
                                    </div>
                                    <div style={{ ...style.bubble, ...(m.quem === "voce" ? style.bubbleMe : {}) }}>{m.texto}</div>
                                </div>
                            ))}
                        </div>

                        <div style={style.tecladoCard}>
                            <div style={style.linhaTopo} />
                            <textarea
                                aria-label="Sua resposta"
                                style={style.textarea}
                                placeholder="Digite sua resposta ou use o botão de microfone…"
                                value={texto}
                                disabled={!podeResponder}
                                onChange={(e) => setTexto(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === "Enter" && !e.shiftKey) {
                                        e.preventDefault();
                                        enviarTexto();
                                    }
                                }}
                            />
                            <div style={style.composeFoot}>
                                <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Shift + Enter para nova linha</span>
                                <button style={style.responderBtn} disabled={!podeResponder} onClick={enviarTexto} aria-label="Enviar resposta">
                                    <Send size={15} />
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                )}
            </div>
        </Shell>
    );
}