import { useState } from "react";
import React from "react";
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
        <div style={style.root}>
            <style>{FONTS}</style>
            <div style={style.card}>
                <div style={style.avatar}>

                </div>
                <p style={style.greeting}> Olá! sou o {INTERVIEWER}, seu entrevistador virtual.</p>
                <h2 style={style.title}>Vamos Começar?</h2>
                <h5 style={style.subtitle}>Durante a entrevista, farei algumas perguntas por voz sobre sua experiência, conhecimentos e habilidades.</h5>
                <div style={style.instructions}>
                    <div style={style.info}>
                        <div style={style.infoIcon}>
                            <Mic size={20} />
                        </div>
                        <span style={{color: "#5c5c5c",}}>Certifique-se de que seu microfone esteja funcionando corretamente.</span>

                    </div>
                </div>
            </div>
        </div>
    );
}

const FONTS = `
@import url('https://fonts.googleapis.com/css2?family=Coiny&family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=Lexend:wght@700&family=Momo+Trust+Display&family=Momo+Trust+Sans:wght@200..800&family=Paytone+One&family=Silkscreen:wght@400;700&display=swap');`

const style = {
    root: {
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: 24,
        backgroundColor: "#e4f3f0",
    },
    card: {
        width: 400,
        height: 600,
        textAlign: "center",
        backgroundColor: "white",
        placeItems: "center",
        borderRadius: 8,
        padding: 24,
    },
    greeting: {
        fontFamily: "dm sans",
        marginTop: 20,
        fontSize: 15,
         color: "#5c5c5c",
    },
    title: {
        fontFamily: "dm sans",
        marginTop: 10,
    },
    subtitle: {
        fontFamily: "dm sans",
        marginTop: 20,
        fontSize: 15,
        fontWeight: 400,
       color: "#5c5c5c",
    },
    avatar: {
        width: 64,
        height: 64,
        marginTop: 25,
        borderRadius: 32,
        placeItems: "center",
        background: `
  radial-gradient(circle at left center, #e2aed1, transparent 50%),
  radial-gradient(circle at right center, #b6cf99, transparent 50%),
  radial-gradient(circle at center bottom, #ff743d, transparent 55%),
  #f1faff
`
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

};
