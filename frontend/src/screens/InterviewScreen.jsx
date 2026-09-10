import { useState, useRef, useEffect } from "react";
import React from "react";
import { useNavigate } from "react-router-dom";
import SideBar from "../components/SideBar";
import Avatar from "../components/Avatar";
import { Mic, Square, Send, Volume2, XCircle, Clock } from "lucide-react";

const INTERVIEWER = "du";
 
const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
console.log("API =", API);
 
export default function InterviewScreen() {
    const navigate = useNavigate();
 
    const [sessionId, setSessionId] = useState(null);
    const [perguntaAtual, setPerguntaAtual] = useState("");
    const [indiceAtual, setIndiceAtual] = useState(0);
    const [turno, setTurno] = useState("interviewer");
    const [gravando, setGravando] = useState(false);
    const [processando, setProcessando] = useState(false); 
    const [finalizada, setFinalizada] = useState(false);
    const [segundos, setSegundos] = useState(0);
    const [transcricao, setTranscricao] = useState([]);
    const [texto, setTexto] = useState("");
 
    const mediaRecorderRef = useRef(null);
    const chunksRef = useRef([]);
    const audioRef = useRef(null);
    const iniciadoRef = useRef(false);
    const msgsRef = useRef(null);

    useEffect(() => {
        const el = msgsRef.current;
        if (el) el.scrollTop = el.scrollHeight;
    }, [transcricao]);
 
   
    useEffect(() => {
        const t = setInterval(() => setSegundos((s) => s + 1), 1000);
        return () => clearInterval(t);
    }, []);
 
   
    useEffect(() => {
        if (iniciadoRef.current) return;
        iniciadoRef.current = true;
        iniciarSessao();
        return () => audioRef.current?.pause();
    }, []);
 
    function agora() {
        return new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    }
    function mmss(s) {
        const m = String(Math.floor(s / 60)).padStart(2, "0");
        const seg = String(s % 60).padStart(2, "0");
        return `${m}:${seg}`;
    }
 
    
    async function iniciarSessao() {
        try {
            const res = await fetch(`${API}/session`, { method: "POST" });
            if (!res.ok) throw new Error();
            const data = await res.json(); 
            setSessionId(data.session_id);
            await apresentarFala(data.pergunta, 0, false);
        } catch {
            alert("Não consegui iniciar a entrevista. O backend está no ar?");
        }
    }
 
    
    async function falar(fala) {
        try {
            const res = await fetch(`${API}/voice/fala`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ texto: fala }),
            });
            if (!res.ok) throw new Error();
            const blob = await res.blob();
            const audio = new Audio(URL.createObjectURL(blob));
            audioRef.current = audio;
            await new Promise((resolve) => {
                audio.onended = resolve;
                audio.onerror = resolve;
               
                audio.play().catch(resolve);
            });
        } catch {
         
        }
    }
 

    async function apresentarFala(fala, indice, terminou) {
        setPerguntaAtual(fala);
        if (typeof indice === "number") setIndiceAtual(indice);
        setTranscricao((prev) => [...prev, { quem: "ia", texto: fala, hora: agora() }]);
        setTurno("interviewer");
        await falar(fala);
        if (terminou) {
            setFinalizada(true);
            setTimeout(() => navigate("/feedback", { state: { sessionId } }), 1200);
        } else {
            setTurno("voce");
        }
    }
 
  
    async function enviarResposta(conteudo) {
        const msg = (conteudo ?? "").trim();
        if (!msg || !sessionId || processando) return;
 
        setTranscricao((prev) => [...prev, { quem: "voce", texto: msg, hora: agora() }]);
        setTexto("");
        setProcessando(true);
        setTurno("interviewer"); 
 
        try {
            const res = await fetch(`${API}/turn/${sessionId}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ texto: msg }),
            });
            if (!res.ok) throw new Error();
            const data = await res.json(); 
            await apresentarFala(data.fala, data.indice_atual, data.finalizada);
        } catch {
            alert("Erro ao enviar a resposta.");
            setTurno("voce");
        } finally {
            setProcessando(false);
        }
    }
 
    
 
    async function comecarGravacao() {
        if (turno !== "voce" || processando) return;
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const recorder = new MediaRecorder(stream);
            chunksRef.current = [];
            recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
            recorder.onstop = async () => {
                stream.getTracks().forEach((t) => t.stop());
                const blob = new Blob(chunksRef.current, { type: "audio/webm" });
                await responderPorVoz(blob);
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
 
   
    async function responderPorVoz(blob) {
        setProcessando(true);
        try {
            const form = new FormData();
            form.append("file", blob, "audio.webm");
            const res = await fetch(`${API}/voice/transcricao`, { method: "POST", body: form });
            if (!res.ok) throw new Error();
            const data = await res.json(); 
            setProcessando(false);
            await enviarResposta(data.texto);
        } catch {
            setProcessando(false);
            alert("Falha ao transcrever o áudio.");
        }
    }
 
   
 
    const podeResponder = turno === "voce" && !processando && !finalizada;
    const ouvindo = turno === "voce" && gravando;
    const iaFalando = turno === "interviewer" && !processando;
 
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
                        <button style={style.concluirBtn} onClick={async () => {
                            if (sessionId) {
                                try { await fetch(`${API}/session/${sessionId}/finish`, { method: "POST" }); } catch {}
                            }
                            navigate("/feedback", { state: { sessionId } });
                        }}>
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
 
                            <p style={style.status}>{statusTexto}</p>
 
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
                                <p style={{ margin: 0, fontSize: 12.5, color: "#8a93ab" }}>Status</p>
                                <p style={{ margin: "2px 0 0", fontSize: 14, fontWeight: 700, color: "#a7d4cb" }}>
                                    {processando ? "Processando…" : podeResponder ? "Pronta para ouvir" : "Aguarde…"}
                                </p>
                            </div>
                            <button
                                style={{ ...style.micBtn, opacity: podeResponder ? 1 : 0.5, cursor: podeResponder ? "pointer" : "default" }}
                                disabled={!podeResponder}
                                onClick={gravando ? pararGravacao : comecarGravacao}
                            >
                                {gravando ? <Square size={18} fill="#fff" /> : <Mic size={18} />}
                                <span style={{ lineHeight: 1.1 }}>{gravando ? "Enviar resposta" : "Falar ao Microfone"}</span>
                            </button>
                        </div>
                    </div>
 
                    <div style={style.colRight}>
                        <div style={style.transcricao}>
                            <span style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 700, color: "#26443F", fontSize: 15 }}>
                                Transcrição ao Vivo
                            </span>
                            <span style={style.pill}>Tempo Real</span>
                        </div>
 
                        <div style={style.msgs} ref={msgsRef}>
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
                                style={style.textarea}
                                placeholder="Digite sua resposta ou use o botão de microfone…"
                                value={texto}
                                disabled={!podeResponder}
                                onChange={(e) => setTexto(e.target.value)}
                                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); enviarResposta(texto); } }}
                            />
                            <div style={style.composeFoot}>
                                <span style={{ fontSize: 12, color: "#6a7391" }}>Shift + Enter para nova linha</span>
                                <button style={style.responderBtn} disabled={!podeResponder} onClick={() => enviarResposta(texto)}>
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
 
const CSS = `
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300..700&display=swap');
.rec-dot{width:9px;height:9px;border-radius:50%;background:#f0526b;animation:pulseRed 1.4s infinite}
.online-dot{width:8px;height:8px;border-radius:50%;background:#38d39f}
@keyframes pulseRed{0%{box-shadow:0 0 0 0 rgba(240,82,107,.6)}70%{box-shadow:0 0 0 8px rgba(240,82,107,0)}100%{box-shadow:0 0 0 0 rgba(240,82,107,0)}}
.bar{width:4px;height:8px;border-radius:99px;background:#39415f}
.bar.on{background:linear-gradient(#a0c9ca,#F87060);animation:wave .9s ease-in-out infinite}
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
        borderRadius: 20,
        border: "1px solid #CDE1DC",
        padding: "14px 18px",
        marginBottom: 18,
    },
    recTag: {
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        color: "#26443F",
        fontWeight: 700,
        fontSize: 12.5,
        letterSpacing: .3,
    },
    pill: {
        fontSize: 12,
        fontWeight: 600,
        color: "#26443F",
        background: "#F4F8F7",
        border: "none",
        borderRadius: 18,
        padding: "4px 9px",
    },
    timer: {
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        color: "#26443F",
        background: "#F4F8F7",
        border: "1px solid #CDE1DC",
        borderRadius: 20,
        padding: "7px 12px",
        fontWeight: 600,
        fontSize: 12,
    },
    concluirBtn: {
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        background: "#ff000015",
        color: "#8d0606",
        border: "1px solid #8f575733",
        borderRadius: 20,
        padding: "7px 12px",
        fontWeight: 600,
        fontSize: 12,
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
        minWidth: 380,
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
        minHeight: 560,
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
        background: "#F4F8F7",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 110,
        height: 30,
        color: "#26443F",
        border: "1px solid #CDE1DC",
        borderRadius: 20,
        fontWeight: 700,
        fontSize: 12,
        letterSpacing: .3,
        gap: 6,
    },
    avatarWrap: {
        marginTop: 18,
    },
    status: {
        marginTop: 20,
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
    questionCard: {
        width: "100%",
        background: "#F4F8F7",
        border: "1px solid #CDE1DC",
        borderRadius: 14,
        padding: "16px 18px",
        marginTop: 20,
        boxSizing: "border-box",
    },
    qHead: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 8,
    },
    perguntaNum: {
        background: "#F4F8F7",
        width: 110,
        display: "inline-flex",
        justifyContent: "center",
        alignItems: "center",
        height: 24,
        color: "#26443F",
        border: "1px solid #CDE1DC",
        borderRadius: 20,
        fontWeight: 700,
        fontSize: 12,
        letterSpacing: .3,
        gap: 6,
    },
    tipo: {
        fontSize: 12,
        fontWeight: 700,
        color: "#26443F",
        border: "none",
        borderRadius: 1,
        padding: "3px 9px",
    },
    textoIA: {
        margin: 0,
        color: "#26443F",
        fontSize: 16,
        lineHeight: 1.5,
        fontWeight: 600,
    },
    bottomBar: {
        background: "#ffffff",
        border: "1px solid #CDE1DC",
        borderRadius: 20,
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
        borderRadius: 18,
        padding: "12px 18px",
        fontWeight: 700,
        fontSize: 14,
        background: "#7fa89f",
        flexShrink: 0,
    },
    transcricao: {
        display: "flex",
        color: "#26443F",
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
        color: "#26443F",
        background: "#F4F8F7",
        border: "1px solid #CDE1DC",
        borderRadius: 14,
        borderTopLeftRadius: 2,
        padding: "12px 14px",
        fontSize: 14.5,
        lineHeight: 1.5,
    },
    bubbleMe: {
        background: "linear-gradient(135deg,#33306e,#3a2f6b)",
        border: "1px solid #4a3f86",
        color: "#efeaff",
    },
    tecladoCard: {
        border: "none",
        padding: 14,
    },
    linhaTopo: {
        height: 1,
        background: "#CDE1DC",
        marginLeft: 10,
        marginRight: 10,
        marginBottom: 14,
    },
    textarea: {
        width: "100%",
        minHeight: 64,
        resize: "none",
        background: "#ffffff",
        border: "1px solid #d1e9e4",
        borderRadius: 15,
        padding: "12px 14px",
        color: "#26443F",
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
        borderRadius: 15,
        padding: "9px 16px",
        fontWeight: 700,
        fontSize: 14,
        cursor: "pointer",
    },
};