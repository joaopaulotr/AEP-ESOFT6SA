import { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import SideBar from "../components/SideBar";
import { FileText, ArrowLeft, RefreshCw, AlertCircle, ListChecks } from "lucide-react";
import { api } from "../services/api";
import ThemeToggle from "../components/ThemeToggle";

export default function FeedbackScreen() {
    const navigate = useNavigate();
    const location = useLocation();
    
    const sessionId = location.state?.sessionId ?? null;
    const semRespostas = location.state?.respostas === 0;

    const [sintese, setSintese] = useState("");
    const [carregando, setCarregando] = useState(true);
    const [erro, setErro] = useState("");
    const pediuRef = useRef(false); 

    useEffect(() => {
        if (pediuRef.current) return;
        pediuRef.current = true;
        gerarSintese();
        // eslint-disable-next-line react-hooks/exhaustive-deps -- pede a síntese uma única vez ao montar (guardado por pediuRef)
    }, []);

    async function gerarSintese() {
        if (!sessionId) {
            setErro("Nenhuma sessão encontrada. Volte e faça uma entrevista até o fim.");
            setCarregando(false);
            return;
        }
        if (semRespostas) {
            // Nada do participante para resumir: nem pede ao servidor.
            setErro("A entrevista não tem respostas para resumir.");
            setCarregando(false);
            return;
        }
        setCarregando(true);
        setErro("");
        try {
            const data = await api.generateSynthesis(sessionId);
            setSintese(data.sintese || "");
        } catch (e) {
            setErro(e.detail || "Não consegui gerar a síntese.");
        } finally {
            setCarregando(false);
        }
    }

    return (
        <SideBar>
            <div style={style.root}>
                <style>{CSS}</style>

                <header style={style.topbar}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <span style={style.badge}><FileText size={16} /></span>
                        <div>
                            <p style={style.titulo}>Síntese da Entrevista</p>
                            <p style={style.subtitulo}>Relatório gerado a partir da conversa</p>
                        </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <ThemeToggle />
                        <button style={style.voltarBtn} onClick={() => navigate("/entrevistas")}>
                            <ArrowLeft size={16} aria-hidden="true" /> Ver todas as entrevistas
                        </button>
                    </div>
                </header>

                <div style={style.card} aria-live="polite">
                    {carregando && (
                        <div style={style.estado}>
                            <RefreshCw size={22} className="girando" />
                            <p style={style.estadoTexto}>Gerando síntese… isso pode levar alguns segundos.</p>
                        </div>
                    )}

                    {!carregando && erro && (
                        <div style={style.estado}>
                            <AlertCircle size={22} style={{ color: "var(--color-error)" }} />
                            <p style={{ ...style.estadoTexto, color: "var(--color-error)" }}>{erro}</p>
                            {sessionId && !semRespostas && (
                                <button style={style.retryBtn} onClick={gerarSintese}>
                                    <RefreshCw size={15} /> Tentar de novo
                                </button>
                            )}
                        </div>
                    )}

                    {!carregando && !erro && (
                        <div style={style.relatorio}>{sintese}</div>
                    )}

                    {!carregando && sessionId && (
                        <button style={style.verBtn} onClick={() => navigate(`/sessao/${sessionId}`)}>
                            <ListChecks size={16} /> Ver entrevista completa
                        </button>
                    )}
                </div>
            </div>
        </SideBar>
    );
}

const CSS = `
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300..700&display=swap');
.girando{animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
`;

const style = {
    root: {
        width: "100%",
        boxSizing: "border-box",
        fontFamily: "var(--font-sans)",
    },
    topbar: {
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 16,
        flexWrap: "wrap",
        backgroundColor: "var(--color-surface)",
        borderRadius: 20,
        border: "1px solid var(--color-border)",
        padding: "14px 18px",
        marginBottom: 18,
    },
    badge: {
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 38,
        height: 38,
        borderRadius: 12,
        background: "var(--color-surface-2)",
        border: "1px solid var(--color-border)",
        color: "var(--color-text)",
    },
    titulo: {
        margin: 0,
        color: "var(--color-text)",
        fontWeight: 700,
        fontSize: 16,
    },
    subtitulo: {
        margin: "2px 0 0",
        color: "var(--color-text-muted)",
        fontSize: 12.5,
    },
    voltarBtn: {
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        background: "var(--color-surface-2)",
        color: "var(--color-text)",
        border: "1px solid var(--color-border)",
        borderRadius: 20,
        padding: "8px 14px",
        fontWeight: 600,
        fontSize: 13,
        cursor: "pointer",
        minHeight: "var(--touch-target)",
    },
    card: {
        background: "var(--color-surface)",
        border: "1px solid var(--color-border-soft)",
        borderRadius: 18,
        padding: "clamp(16px, 4vw, 26px)",
        minHeight: 400,
    },
    estado: {
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 14,
        minHeight: 340,
        color: "var(--color-primary-border)",
    },
    estadoTexto: {
        margin: 0,
        fontSize: 14.5,
        fontWeight: 600,
        color: "var(--color-text)",
        textAlign: "center",
        maxWidth: 380,
    },
    retryBtn: {
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        background: "var(--color-primary)",
        color: "var(--color-on-primary)",
        border: "none",
        borderRadius: 14,
        padding: "9px 16px",
        fontWeight: 700,
        fontSize: 13.5,
        cursor: "pointer",
        marginTop: 4,
    },
    verBtn: {
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        marginTop: 20,
        background: "var(--color-surface-2)",
        color: "var(--color-primary)",
        border: "1px solid var(--color-primary-border)",
        borderRadius: 16,
        padding: "0 16px",
        minHeight: "var(--touch-target)",
        fontWeight: 600,
        fontSize: 14,
        cursor: "pointer",
    },
    relatorio: {
        whiteSpace: "pre-wrap",   
        color: "var(--color-text)",
        fontSize: 15,
        lineHeight: 1.65,
    },
};