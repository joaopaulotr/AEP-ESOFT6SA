import { useState } from "react";
import React from "react";
import SideBar from "../components/SideBar";
import Avatar from "../components/Avatar";
import { useNavigate } from "react-router-dom";
import { Mic, Clock, MessageCircle, Check, ArrowRight } from "lucide-react";

const INTERVIEWER = "du";
const NOME = "duda";


export default function WelcomeScreen() {
    const navigate = useNavigate();
    const [micStatus, setMicStatus] = useState("idle");

    async function askMicPermission() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            stream.getTracks().forEach((track) => track.stop());
            setMicStatus("ok");
        } catch {
            setMicStatus("denied");
        }
    }

    const comoFunciona = [
        { ic: <MessageCircle size={20} />, t: "Entrevista conduzida por voz, com uma pergunta por vez." },
        { ic: <Clock size={20} />, t: "Duração aproximada de 15 minutos." },
        { ic: <Mic size={20} />, t: "Utilize o microfone para gravar sua resposta e confirme o envio ao concluir." },
    ];

    return (
        <SideBar>
            <style>{FONTS}</style>

            <div style={style.root}>
              
                <div style={style.card}>
                    <Avatar size={92} />
                    <p style={style.saudacao}>Olá, {NOME}</p>
                    <h1 style={style.title}>Pronto para iniciar sua próxima entrevista?</h1>
                    <p style={style.subtittle}>
                        Ao longo da conversa, você terá a oportunidade de apresentar sua trajetória, demonstrar seus conhecimentos e destacar as competências mais relevantes para a posição.
                    </p>

                  
                    <div style={style.actions}>
                        <button
                            onClick={askMicPermission}
                            disabled={micStatus === "ok"}
                            style={{
                                ...style.micBtn,
                                ...(micStatus === "ok" ? style.micBtnOk : {}),
                                cursor: micStatus === "ok" ? "default" : "pointer",
                            }}
                        >
                            {micStatus === "ok"
                                ? (<><Check size={18} /> Microfone pronto</>)
                                : (<><Mic size={18} /> Permitir microfone</>)}
                        </button>

                        <button
                            onClick={() => navigate("/entrevista")}
                            disabled={micStatus !== "ok"}
                            style={{
                                ...style.startBtn,
                                opacity: micStatus === "ok" ? 1 : 0.45,
                                cursor: micStatus === "ok" ? "pointer" : "default",
                            }}
                        >
                            Começar entrevista <ArrowRight size={18} />
                        </button>
                    </div>

                    {micStatus === "denied" && (
                        <p style={style.aviso}>Não foi possível acessar o microfone. Verifique a permissão do navegador.</p>
                    )}
                    {micStatus !== "ok" && micStatus !== "denied" && (
                        <p style={style.hint}>Libere o microfone para iniciar a entrevista.</p>
                    )}
                </div>

                
                <div style={style.infoRow}>
                    {comoFunciona.map((x, i) => (
                        <div key={i} style={style.infoCard}>
                            <div style={style.infoIcon}>{x.ic}</div>
                            <span style={style.infoText}>{x.t}</span>
                        </div>
                    ))}
                </div>
            </div>
        </SideBar>
    );
}

const FONTS = `
@import url('https://fonts.googleapis.com/css2?family=Coiny&family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=Lexend:wght@700&family=Momo+Trust+Display&family=Momo+Trust+Sans:wght@200..800&family=Paytone+One&family=Silkscreen:wght@400;700&display=swap');`;

const style = {
    root: {
        width: "100%",
        maxWidth: 860,
        margin: "0 auto",
        minHeight: "80vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 32,
        padding: "24px 0",
        boxSizing: "border-box",
    },
    card: {
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center",
        width: "100%",
    },
    saudacao: {
        margin: "22px 0 0",
        fontFamily: "dm sans",
        fontSize: 15,
        color: "#6a7d77",
    },
    title: {
        margin: "10px 0 0",
        fontFamily: "Momo Trust Sans",
        fontSize: 37,
        fontWeight: 700,
        lineHeight: 1.12,
        letterSpacing: "-0.02em",
        color: "#1f2d29",
        maxWidth: 680,
    },
    subtittle: {
        margin: "16px 0 0",
        fontFamily: "dm sans",
        fontSize: 16,
        lineHeight: 1.6,
        color: "#6a7d77",
        maxWidth: 660,
    },
    vaga: {
        marginTop: 22,
        padding: "7px 16px",
        borderRadius: 999,
        fontFamily: "dm sans",
        fontSize: 13.5,
        fontWeight: 600,
        color: "#4f776e",
        backgroundColor: "#e9f3f0",
        border: "1px solid #d6ebe3",
    },
    actions: {
        marginTop: 26,
        display: "flex",
        gap: 12,
        flexWrap: "wrap",
        justifyContent: "center",
    },
    micBtn: {
        height: 50,
        padding: "0 22px",
        backgroundColor: "#ffffff",
        borderRadius: 18,
        border: "1px solid #7fa89f",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        color: "#4f776e",
        fontFamily: "dm sans",
        fontWeight: 600,
        fontSize: 15,
    },
    micBtnOk: {
        backgroundColor: "#e9f3f0",
        border: "1px solid #cfe6df",
    },
    startBtn: {
        height: 50,
        padding: "0 26px",
        backgroundColor: "#4f776e",
        borderRadius: 18,
        border: "none",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 9,
        color: "#ffffff",
        fontFamily: "dm sans",
        fontWeight: 600,
        fontSize: 15,
        boxShadow: "0 10px 26px -14px rgba(31,45,41,.7)",
    },
    aviso: {
        margin: "16px 0 0",
        fontFamily: "dm sans",
        fontSize: 13,
        fontWeight: 600,
        color: "#c9563b",
    },
    hint: {
        margin: "14px 0 0",
        fontFamily: "dm sans",
        fontSize: 13,
        color: "#9db3ac",
    },
    infoRow: {
        width: "100%",
        display: "flex",
        gap: 12,
        flexWrap: "wrap",
        justifyContent: "center",
    },
    infoCard: {
        flex: "1 1 210px",
        minWidth: 200,
        display: "flex",
        alignItems: "center",
        gap: 12,
        backgroundColor: "#ffffff",
        border: "1px solid #d1e9e4",
        borderRadius: 18,
        padding: "14px 16px",
    },
    infoIcon: {
        width: 40,
        height: 40,
        flexShrink: 0,
        borderRadius: 18,
        display: "grid",
        placeItems: "center",
        color: "#4f776e",
        backgroundColor: "#e9f3f0",
    },
    infoText: {
        fontFamily: "dm sans",
        fontSize: 14,
        lineHeight: 1.4,
        color: "#41524d",
        textAlign: "left",
    },
};