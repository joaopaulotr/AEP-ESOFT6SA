import { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import React from "react";
import SideBar from "../components/SideBar";
import { FileText, ArrowLeft, RefreshCw, AlertCircle } from "lucide-react";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function FeedbackScreen() {
    const navigate = useNavigate();
    const location = useLocation();
    
    const sessionId = location.state?.sessionId ?? null;

    const [sintese, setSintese] = useState("");
    const [carregando, setCarregando] = useState(true);
    const [erro, setErro] = useState("");
    const pediuRef = useRef(false); 

    useEffect(() => {
        if (pediuRef.current) return;
        pediuRef.current = true;
        gerarSintese();
    }, []);

    async function gerarSintese() {
        if (!sessionId) {
            setErro("Nenhuma sessão encontrada. Volte e faça uma entrevista até o fim.");
            setCarregando(false);
            return;
        }
        setCarregando(true);
        setErro("");
        try {
            const res = await fetch(`${API}/session/${sessionId}/synthesis`, { method: "POST" });
            if (!res.ok) {
                
                let detalhe = "";
                try {
                    const j = await res.json();
                    detalhe = j.detail || "";
                } catch {  }
                throw new Error(detalhe || "Falha ao gerar a síntese.");
            }
            const data = await res.json();
            setSintese(data.sintese || "");
        } catch (e) {
            setErro(e.message || "Não consegui gerar a síntese.");
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
                    <button style={style.voltarBtn} onClick={() => navigate("/")}>
                        <ArrowLeft size={16} /> Voltar
                    </button>
                </header>

                <div style={style.card}>
                    {carregando && (
                        <div style={style.estado}>
                            <RefreshCw size={22} className="girando" />
                            <p style={style.estadoTexto}>Gerando síntese… isso pode levar alguns segundos.</p>
                        </div>
                    )}

                    {!carregando && erro && (
                        <div style={style.estado}>
                            <AlertCircle size={22} color="#b4453f" />
                            <p style={{ ...style.estadoTexto, color: "#b4453f" }}>{erro}</p>
                            {sessionId && (
                                <button style={style.retryBtn} onClick={gerarSintese}>
                                    <RefreshCw size={15} /> Tentar de novo
                                </button>
                            )}
                        </div>
                    )}

                    {!carregando && !erro && (
                        <div style={style.relatorio}>{sintese}</div>
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
    badge: {
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 38,
        height: 38,
        borderRadius: 12,
        background: "#F4F8F7",
        border: "1px solid #CDE1DC",
        color: "#26443F",
    },
    titulo: {
        margin: 0,
        color: "#26443F",
        fontWeight: 700,
        fontSize: 16,
    },
    subtitulo: {
        margin: "2px 0 0",
        color: "#8a93ab",
        fontSize: 12.5,
    },
    voltarBtn: {
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        background: "#F4F8F7",
        color: "#26443F",
        border: "1px solid #CDE1DC",
        borderRadius: 20,
        padding: "8px 14px",
        fontWeight: 600,
        fontSize: 13,
        cursor: "pointer",
    },
    card: {
        background: "#ffffff",
        border: "1px solid #d1e9e4",
        borderRadius: 18,
        padding: 26,
        minHeight: 400,
    },
    estado: {
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 14,
        minHeight: 340,
        color: "#7fa89f",
    },
    estadoTexto: {
        margin: 0,
        fontSize: 14.5,
        fontWeight: 600,
        color: "#26443F",
        textAlign: "center",
        maxWidth: 380,
    },
    retryBtn: {
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        background: "#7fa89f",
        color: "#fff",
        border: "none",
        borderRadius: 14,
        padding: "9px 16px",
        fontWeight: 700,
        fontSize: 13.5,
        cursor: "pointer",
        marginTop: 4,
    },
    relatorio: {
        whiteSpace: "pre-wrap",   
        color: "#26443F",
        fontSize: 15,
        lineHeight: 1.65,
    },
};