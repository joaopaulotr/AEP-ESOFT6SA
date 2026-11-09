import React from "react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Mic, Square, Send, Volume2, XCircle, Clock } from "lucide-react";
import SideBar from "../components/SideBar";
import Avatar from "../components/Avatar";
import ThemeToggle from "../components/ThemeToggle";
import { useInterviewSession } from "../hooks/useInterviewSession";
import { useRecorder } from "../hooks/useRecorder";
import { useElapsedTime } from "../hooks/useElapsedTime";
import { mmss } from "../utils/tempo";
import { style, CSS } from "./InterviewScreen.styles";

const INTERVIEWER = "du";

export default function InterviewScreen() {
    const navigate = useNavigate();
    const [texto, setTexto] = useState("");
    const msgsRef = useRef(null);
    const segundos = useElapsedTime();

    const sessao = useInterviewSession({
        onFinished: (sessionId) => navigate("/feedback", { state: { sessionId } }),
    });
    const { perguntaAtual, indiceAtual, turno, processando, finalizada, transcricao, erro } = sessao;

    const recorder = useRecorder({ onRecorded: sessao.enviarAudio });

    useEffect(() => {
        const el = msgsRef.current;
        if (el) el.scrollTop = el.scrollHeight;
    }, [transcricao]);

    useEffect(() => {
        if (erro) alert(erro.mensagem);
    }, [erro]);

    const podeResponder = turno === "voce" && !processando && !finalizada;
    const ouvindo = turno === "voce" && recorder.gravando;
    const iaFalando = turno === "interviewer" && !processando && !finalizada;

    async function comecarGravacao() {
        if (!podeResponder) return;
        try {
            await recorder.start();
        } catch {
            alert("Não consegui acessar o microfone.");
        }
    }

    function enviarTexto() {
        if (!podeResponder || !texto.trim()) return;
        sessao.enviarResposta(texto);
        setTexto("");
    }

    const statusTexto = processando
        ? "PROCESSANDO…"
        : ouvindo
        ? "OUVINDO SUA RESPOSTA…"
        : iaFalando
        ? `${INTERVIEWER.toUpperCase()} ESTÁ FALANDO…`
        : finalizada
        ? "ENTREVISTA ENCERRADA"
        : "SUA VEZ DE RESPONDER";

    return (
        <SideBar>
            <div style={style.root}>
                <style>{CSS}</style>

                <header style={style.topbar}>
                    <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
                        <span style={style.recTag}><span className="rec-dot" /> ENTREVISTA EM ANDAMENTO</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <span style={style.timer}><Clock size={15} /> {mmss(segundos)}</span>
                        <ThemeToggle />
                        <button style={style.concluirBtn} onClick={sessao.concluir}>
                            <XCircle size={17} /> Concluir
                        </button>
                    </div>
                </header>

                <div style={style.row}>
                    <div style={style.colLeft}>
                        <div style={style.aiPanel}>
                            <div style={style.panelHead}>
                                <span style={style.perguntaNum}>Pergunta {indiceAtual + 1}</span>
                                <span style={style.voiceChip}><Volume2 size={14} /> Voz: Ativada</span>
                            </div>

                            <div style={style.avatarWrap}>
                                <Avatar size={128} />
                            </div>

                            <p style={style.status} role="status">{statusTexto}</p>

                            <div style={style.wave}>
                                {[0, 1, 2, 3, 4, 5, 6].map((i) => (
                                    <span key={i} className={ouvindo || iaFalando ? "bar on" : "bar"} style={{ animationDelay: `${i * 0.09}s` }} />
                                ))}
                            </div>

                            <div style={style.questionCard}>
                                <p style={style.textoIA}>
                                    {perguntaAtual ? `"${perguntaAtual}"` : "Conectando à entrevista…"}
                                </p>
                            </div>
                        </div>

                        <div style={style.bottomBar}>
                            <div style={{ flex: 1 }}>
                                <p style={{ margin: 0, fontSize: 12.5, color: "var(--color-text-muted)" }}>Status</p>
                                <p style={{ margin: "2px 0 0", fontSize: 14, fontWeight: 700, color: "var(--color-status)" }}>
                                    {processando ? "Processando…" : podeResponder ? "Pronta para ouvir" : "Aguarde…"}
                                </p>
                            </div>
                            <button
                                className="mic-btn"
                                aria-label={recorder.gravando ? "Parar e enviar resposta" : "Falar ao microfone"}
                                style={{ ...style.micBtn, opacity: podeResponder ? 1 : 0.5, cursor: podeResponder ? "pointer" : "default" }}
                                disabled={!podeResponder}
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

                        <div style={style.msgs} ref={msgsRef} aria-live="polite" aria-label="Transcrição da entrevista">
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
            </div>
        </SideBar>
    );
}
