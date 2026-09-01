import { useState } from "react";
import React from "react";
import Avatar from "../components/Avatar";
import Layout from "../components/Layout";

import { Mic, Clock, MessageCircle, Check, ArrowRight } from "lucide-react";

const INTERVIEWER = "interviewer";

export default function WelcomeScreen({ onStart }) {
    const [micStatus, setMicStatus] = useState("idle");

    async function askMicPermission() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            stream.getTracks().forEach(track => track.stop());
            setMicStatus("ok");
        } catch {
            setMicStatus("denied");
        }
    }

    return (
        <Layout>
            <style>{FONTS}</style>
            <div style={style.card}>
                <Avatar />
                <p style={style.greeting}> Olá! sou o {INTERVIEWER}, seu entrevistador virtual.</p>
                <h2 style={style.title}>Vamos Começar?</h2>
                <h5 style={style.subtitle}>Ao longo da conversa, você terá a oportunidade de apresentar sua trajetória, demonstrar seus conhecimentos e destacar as competências mais relevantes para a posição.</h5>
                <div style={style.instructions}>
                    <div style={style.instructions}>
                        <div style={style.info}>
                            <div style={style.infoIcon}>
                                <MessageCircle size={20} />
                            </div>
                            <span style={{ color: "#5c5c5c" }}>Entrevista conduzida por voz, com uma pergunta por vez.</span>
                        </div>

                        <div style={style.info}>
                            <div style={style.infoIcon}>
                                <Clock size={20} />
                            </div>
                            <span style={{ color: "#5c5c5c" }}>Duração aproximada de 10 minutos.</span>
                        </div>

                        <div style={style.info}>
                            <div style={style.infoIcon}>
                                <Mic size={20} />
                            </div>
                            <span style={{ color: "#5c5c5c" }}>Utilize o microfone para gravar sua resposta e confirme o envio ao concluir.</span>
                        </div>
                    </div>
                </div>
                <button
                    onClick={askMicPermission}
                    disabled={micStatus === "ok"}
                    style={{
                        ...style.micButton,
                        ...(micStatus === "ok" ? style.micBtnOk : {}),
                        cursor: micStatus === "ok" ? "default" : "pointer",
                    }}
                >
                    {micStatus === "ok" ? (
                        <><Check size={18} /> Microfone pronto</>
                    ) : (
                        <><Mic size={18} /> Permitir microfone</>
                    )}
                </button>

                <button
                    onClick={onStart}
                    disabled={micStatus !== "ok"}
                    style={{
                        ...style.startBtn,
                        opacity: micStatus === "ok" ? 1 : 0.45,
                        cursor: micStatus === "ok" ? "default" : "pointer",
                    }}
                >
                    Começar entrevista <ArrowRight size={18} />
                </button>
            </div>
        </Layout>
    );
}

const FONTS = `
@import url('https://fonts.googleapis.com/css2?family=Coiny&family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=Lexend:wght@700&family=Momo+Trust+Display&family=Momo+Trust+Sans:wght@200..800&family=Paytone+One&family=Silkscreen:wght@400;700&display=swap');`

const style = {

    card: {
        width: 400,
        height: 600,
        textAlign: "center",
        backgroundColor: "white",
        placeItems: "center",
        borderRadius: 18,
        padding: 24,
        boxShadow: "0 12px 40px #2A262212, 0 2px 6px #2A26220A",
    },
    greeting: {
        fontFamily: "dm sans",
        marginTop: 20,
        fontSize: 15,
        color: "#5c5c5c",
    },
    title: {
        fontFamily: "Momo Trust Sans",
        marginTop: 10,
        fontWeight: 800,
    },
    subtitle: {
        fontFamily: "dm sans",
        marginTop: 20,
        fontSize: 15,
        fontWeight: 400,
        color: "#5c5c5c",
    },


    instructions: {
        display: "flex",
        flexDirection: "column",
        gap: 10,
        width: "100%",
        textAlign: "left",
    },

    info: {
        display: "flex",
        alignItems: "center",
        justifyContent: "flex-start",
        textAlign: "left",
        fontFamily: "dm sans",
        fontSize: 14,
    },
    infoIcon: {
        width: 40,
        height: 40,
        marginRight: 10,
        display: "grid",
        placeItems: "center",
        flexShrink: 0,
        color: "#7fa89f",
        backgroundColor: "#e4f3f0",
        borderRadius: 10,

    },
    micButton: {
        width: 400,
        height: 40,
        marginTop: 30,
        backgroundColor: "#ffffff",
        borderRadius: 20,
        border: "1px solid #7fa89f",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        color: "#7fa89f",

    },
    startBtn: {
        width: 400,
        height: 40,
        marginTop: 15,
        backgroundColor: "#7fa89f",
        borderRadius: 20,
        border: "1px solid #7fa89f",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 8,
        color: "white",
    }
};
