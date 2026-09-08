import { useState, useRef, useEffect } from "react";
import React from "react";
import { useNavigate } from "react-router-dom";
import SideBar from "../components/SideBar";
import Avatar from "../components/Avatar";
import { Mic, Square, Send, Volume2, XCircle, Clock } from "lucide-react";

const INTERVIEWER = "du";


const PERGUNTAS = [
    { tipo: "Técnica", texto: "Em um projeto TypeScript com React, como você utiliza Generics e Utility Types para garantir que seus componentes sejam flexíveis, porém mantendo uma tipagem rigorosa e segura?" },
    { tipo: "Técnica", texto: "Como você gerencia estado global em uma aplicação React de médio porte? Compare as abordagens que já usou." },
    { tipo: "Comportamental", texto: "Conte sobre uma vez em que você teve um desacordo técnico com o time e como chegaram a uma decisão." },
    { tipo: "Técnica", texto: "Que estratégias você aplica para otimizar performance e evitar re-renderizações desnecessárias?" },
    { tipo: "Comportamental", texto: "Por que essa vaga faz sentido pra você e o que espera dos próximos anos?" },
];

export default function InterviewScreen() {
    const navigate = useNavigate();
    const [gravando, setGravando] = useState(false);
    const [turno, setTurno] = useState("interviewer");
    const [idx, setIdx] = useState(0);
    const [segundos, setSegundos] = useState(0);
    const [transcricao, setTranscricao] = useState([]);
    const [texto, setTexto] = useState("");

    const mediaRecorderRef = useRef(null);
    const chunksRef = useRef([]);

    const atual = PERGUNTAS[idx];

    useEffect(() => {
        const t = setInterval(() => setSegundos((s) => s + 1), 1000);
        return () => clearInterval(t);
    }, []);

    useEffect(() => {
        setTurno("interviewer");
        setTranscricao((prev) => [...prev, { quem: "ia", texto: atual.texto, hora: agora() }]);
        const t = setTimeout(() => setTurno("voce"), 2600);
        return () => clearTimeout(t);
    }, [idx]);

    function agora() {
        return new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    }
    function mmss(s) {
        const m = String(Math.floor(s / 60)).padStart(2, "0");
        const seg = String(s % 60).padStart(2, "0");
        return `${m}:${seg}`;
    }

    async function comecarGravacao() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const recorder = new MediaRecorder(stream);
            chunksRef.current = [];
            recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
            recorder.onstop = () => {
                stream.getTracks().forEach((t) => t.stop());
               
                responder(" Resposta enviada por voz");
            };
            recorder.start();
            mediaRecorderRef.current = recorder;
            setGravando(true);
        } catch {
            alert("Não consegui acessar o microfone.");
        }
    }

    function pararGravacao() {
        mediaRecorderRef.current?.stop();
        setGravando(false);
    }

    function responder(msg) {
        const conteudo = (msg ?? texto).trim();
        if (!conteudo || turno !== "voce") return;
        setTranscricao((prev) => [...prev, { quem: "voce", texto: conteudo, hora: agora() }]);
        setTexto("");
        avancar();
    }

    function avancar() {
        if (idx < PERGUNTAS.length - 1) {
            setIdx((i) => i + 1);
        } else {
            navigate("/feedback"); 
        }
    }

    const ouvindo = turno === "voce" && gravando;
    const iaFalando = turno === "interviewer";

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
                        <button style={style.concluirBtn} onClick={() => navigate("/feedback")}>
                            <XCircle size={17} /> Concluir & Gerar Feedback
                        </button>
                    </div>
                </header>


                <div style={style.row}>

                    <div style={style.colLeft}>
                        <div style={style.aiPanel}>
                            <div style={style.panelHead}>
                                <span style={style.online}><span className="online-dot" /> ENTREVISTADORA IA ({INTERVIEWER.toUpperCase()})</span>
                                <span style={style.voiceChip}><Volume2 size={14} /> Voz da IA: Ativada</span>
                            </div>

                            <div style={style.avatarWrap}>
                                <Avatar size={128} />
                            </div>

                            <p style={style.status}>
                                {ouvindo ? "OUVINDO SUA RESPOSTA…" : iaFalando ? `${INTERVIEWER.toUpperCase()} ESTÁ FALANDO…` : "SUA VEZ DE RESPONDER"}
                            </p>

                            <div style={style.wave}>
                                {[0, 1, 2, 3, 4, 5, 6].map((i) => (
                                    <span key={i} className={ouvindo || iaFalando ? "bar on" : "bar"} style={{ animationDelay: `${i * 0.09}s` }} />
                                ))}
                            </div>

                            <div style={style.qCard}>
                                <div style={style.qHead}>
                                    <span style={style.qLabel}>PERGUNTA ATUAL ({idx + 1}/{PERGUNTAS.length})</span>
                                    <span style={style.qTipo}>{atual.tipo}</span>
                                </div>
                                <p style={style.qTexto}>"{atual.texto}"</p>
                            </div>
                        </div>

                        <div style={style.bottomBar}>
                            <div style={{ flex: 1 }}>
                                <p style={{ margin: 0, fontSize: 12.5, color: "#8a93ab" }}>Status</p>
                                <p style={{ margin: "2px 0 0", fontSize: 14, fontWeight: 700, color: "#a7d4cb" }}>● Pronta para ouvir</p>
                            </div>
                            <button
                                style={{ ...style.micBtn, opacity: turno === "voce" ? 1 : 0.5, cursor: turno === "voce" ? "pointer" : "default" }}
                                disabled={turno !== "voce"}
                                onClick={gravando ? pararGravacao : comecarGravacao}
                            >
                                {gravando ? <Square size={18} fill="#fff" /> : <Mic size={18} />}
                                <span style={{ lineHeight: 1.1 }}>{gravando ? "Enviar resposta" : "Falar ao Microfone"}</span>
                            </button>
                        </div>
                    </div>


                    <div style={style.colRight}>
                        <div style={style.transHead}>
                            <span style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 700, color: "#e7eaf3", fontSize: 15 }}>
                                💬 Transcrição ao Vivo
                            </span>
                            <span style={style.pill}>IA Interativa</span>
                        </div>

                        <div style={style.msgs}>
                            {transcricao.map((m, i) => (
                                <div key={i} style={{ alignSelf: m.quem === "ia" ? "flex-start" : "flex-end", maxWidth: "88%" }}>
                                    <div style={style.msgMeta}>
                                        {m.quem === "ia" ? `${INTERVIEWER} (IA)` : "Você"} · {m.hora}
                                    </div>
                                    <div style={{ ...style.bubble, ...(m.quem === "voce" ? style.bubbleMe : {}) }}>{m.texto}</div>
                                </div>
                            ))}
                        </div>

                        <div style={style.compose}>
                            <textarea
                                style={style.textarea}
                                placeholder="Digite sua resposta ou use o botão de microfone…"
                                value={texto}
                                onChange={(e) => setTexto(e.target.value)}
                                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); responder(); } }}
                            />
                            <div style={style.composeFoot}>
                                <span style={{ fontSize: 12, color: "#6a7391" }}>Shift + Enter para nova linha</span>
                                <button style={style.responderBtn} onClick={() => responder()}>Responder <Send size={15} /></button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </SideBar>
    );
}

const CSS = `
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300..700&display=swap');
.rec-dot{width:9px;height:9px;border-radius:50%;background:#f0526b;animation:pulseRed 1.4s infinite}
.online-dot{width:8px;height:8px;border-radius:50%;background:#38d39f}
@keyframes pulseRed{0%{box-shadow:0 0 0 0 rgba(240,82,107,.6)}70%{box-shadow:0 0 0 8px rgba(240,82,107,0)}100%{box-shadow:0 0 0 0 rgba(240,82,107,0)}}
.bar{width:4px;height:8px;border-radius:99px;background:#39415f}
.bar.on{background:linear-gradient(#8b7bff,#5aa8ff);animation:wave .9s ease-in-out infinite}
@keyframes wave{0%,100%{height:8px}50%{height:24px}}
textarea:focus{outline:none;border-color:#6d5efc !important}
`;

const style = {
    root: {
        width: "100%",
        boxSizing: "border-box",
        fontFamily: "'DM Sans',sans-serif",
    },
    topbar: {
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 16,
        flexWrap: "wrap",
        backgroundColor: "#ffffff",
        borderRadius: 16,
        border: "1px solid #d1e9e4",
        padding: "14px 18px",
        marginBottom: 18,
    },
    recTag: {
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        color: "#f52500",
        fontWeight: 700,
        fontSize: 12.5,
        letterSpacing: .3,
    },
    pill: {
        fontSize: 12,
        fontWeight: 600,
        color: "#ffffff",
        background: "#bb1010",
        border: "none",
        borderRadius: 8,
        padding: "4px 9px",
    },
    timer: {
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        color: "#ffffff",
        background: "#7fa89f",
        border: "none",
        borderRadius: 10,
        padding: "7px 12px",
        fontWeight: 600,
        fontSize: 14,
    },
    concluirBtn: {
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
         background: "#7fa89f",
        color: "#ffffff",
        border: "none",
        borderRadius: 11,
        padding: "9px 15px",
        fontWeight: 700,
        fontSize: 13.5,
        cursor: "pointer",
    },
    row: {
        display: "flex",
        gap: 18,
        alignItems: "stretch",
        flexWrap: "wrap",
    },
    colLeft: {
        flex: "1 1 420px",
        minWidth: 320,
        display: "flex",
        flexDirection: "column",
        gap: 16,
    },
    colRight: {
        flex: "1 1 340px",
        minWidth: 300,
        display: "flex",
        flexDirection: "column",
        background: "#ffffff",
        border: "1px solid #d1e9e4",
        borderRadius: 18,
    },
    aiPanel: {
        background: "#ffffff",
        border: "1px solid #d1e9e4",
        borderRadius: 18,
        padding: 22,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 14,
    },
    panelHead: {
        width: "100%",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        flexWrap: "wrap",
        gap: 8,
    },
    online: {
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        color: "#000000",
        fontWeight: 700,
        fontSize: 12.5,
        letterSpacing: .3,
    },
    voiceChip: {
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        fontSize: 12,
        color: "#ffffff",
        backgroundColor: "#b5ccc7",
        border: "1px solid #a0c4c5",
        borderRadius: 8,
        padding: "4px 9px",
    },
    avatarWrap: {
        marginTop: 8,
    },
    status: {
        margin: 0,
        color: "#b2b4b9",
        fontWeight: 700,
        fontSize: 13,
        letterSpacing: .4,
    },
    wave: {
        display: "flex",
        gap: 5,
        alignItems: "center",
        height: 26,
    },
    qCard: {
        width: "100%",
         backgroundColor: "#e8f1ef",
        border: "1px solid #d1e9e4",
        borderRadius: 14,
        padding: "16px 18px",
        marginTop: 6,
        boxSizing: "border-box",
    },
    qHead: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 8,
    },
    qLabel: {
        color: "#78bda8",
        fontWeight: 700,
        fontSize: 12,
        letterSpacing: .3,
    },
    qTipo: {
        fontSize: 12,
        fontWeight: 700,
        color: "#81aca9",
        background: "#ffffff",
        border: "none",
        borderRadius: 8,
        padding: "3px 9px",
    },
    qTexto: {
        margin: 0,
        color: "#ffffff",
        fontSize: 16,
        lineHeight: 1.5,
        fontWeight: 600,
    },
    bottomBar: {
        background: "#ffffff",
        border: "none",
        borderRadius: 18,
        padding: 14,
        display: "flex",
        alignItems: "center",
        gap: 14,
        flexWrap: "wrap",
    },
    micBtn: {
        display: "inline-flex",
        alignItems: "center",
        gap: 9,
        color: "#fff",
        border: "none",
        borderRadius: 12,
        padding: "12px 18px",
        fontWeight: 700,
        fontSize: 14,
        background: "#7fa89f",
        flexShrink: 0,
    },
    transHead: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "16px 18px",
        borderBottom: "1px solid #a7caca",
    },
    msgs: {
        flex: 1,
        minHeight: 320,
        maxHeight: 520,
        overflowY: "auto",
        padding: 18,
        display: "flex",
        flexDirection: "column",
        gap: 14,
    },
    msgMeta: {
        fontSize: 11.5,
        color: "#7a83a3",
        marginBottom: 5,
    },
    bubble: {
        background: "#7fa89f",
        color: "#ffffff",
        borderRadius: 14,
        padding: "12px 14px",
        fontSize: 14.5,
        lineHeight: 1.5,
    },
    bubbleMe: {
        background: "linear-gradient(135deg,#33306e,#3a2f6b)",
        border: "1px solid #4a3f86",
        color: "#efeaff",
    },
    compose: {
       border: "1px solid #d1e9e4",
        padding: 14,
    },
    textarea: {
        width: "100%",
        minHeight: 64,
        resize: "none",
        background: "#ffffff",
      border: "1px solid #d1e9e4",
        borderRadius: 12,
        padding: "12px 14px",
        color: "#e7eaf3",
        fontSize: 14.5,
        fontFamily: "inherit",
        boxSizing: "border-box",
    },
    composeFoot: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginTop: 10,
    },
    responderBtn: {
        display: "inline-flex",
        alignItems: "center",
        gap: 7,
       background: "#7fa89f",
        color: "#fff",
        border: "none",
        borderRadius: 10,
        padding: "9px 16px",
        fontWeight: 700,
        fontSize: 14,
        cursor: "pointer",
    },
};