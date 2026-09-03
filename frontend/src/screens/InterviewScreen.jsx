import { useState, useRef, useEffect } from "react"
import React from "react";
import Layout from "../components/Layout";
import Avatar from "../components/Avatar";
import Pointer from "../components/Pointer";
import NavBar from "../components/NavBar";
import { Mic, Square, Clock, MessageCircle, Check, ArrowRight, Keyboard } from "lucide-react";

const INTERVIEWER = "interviewer";



export default function InterviewScreen() {
    const [gravando, setGravando] = useState(false);
    const mediaRecorderRef = useRef(null);
    const chunksRef = useRef([]);
    const [falando, setFalando] = useState(false);
    const [turno, setTurno] = useState("interviewer");

    useEffect(() => {
        setTurno("interviewer");
        const timer = setTimeout(() => setTurno("voce"), 3000);
        return () => clearTimeout(timer);
    }, []);
    async function comecarGravacao() {
        try {

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const recorder = new MediaRecorder(stream);
            chunksRef.current = [];


            recorder.ondataavailable = (e) => {
                if (e.data.size > 0) chunksRef.current.push(e.data);
            };


            recorder.onstop = () => {
                stream.getTracks().forEach(t => t.stop());
                const audioBlob = new Blob(chunksRef.current, { type: "audio/webm" });
                enviarAudio(audioBlob);
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

    function enviarAudio(audioBlob) {
        const url = URL.createObjectURL(audioBlob);
        new Audio(url).play();
        setTurno("interviewer");
    }

    function tocarFala(audioBlob) {
        const url = URL.createObjectURL(audioBlob);
        const audio = new Audio(url);

        audio.onplay = () => {
            setFalando(true);
        };
        audio.onended = () => {
            setFalando(false);
            setTurno("voce");
        };

        audio.play();
    }

    return (
        <Layout>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 20, width: "100%", maxWidth: 900, alignSelf: "flex-start", marginTop: 80, }}>

                <div style={style.etapa}>
                    <Pointer style={{marginTop: 20, marginLeft: 20}}/>
                    <span style={{ fontFamily: "DM Sans", fontWeight: "bold", fontSize: 11, color: "#7fa89f", marginLeft: 30, marginTop: 10 }}>ETAPA ATUAL: </span>
                    
                </div>
                <div style={style.painel}>
                    <Avatar size={180} style={{ marginTop: 100, animation: falando ? "pulsar 0.8s ease-in-out infinite" : "pulsar 4s ease-in-out infinite" }} />
                    <div style={style.pergunta}>
                        <span style={{ fontFamily: "DM Sans", fontWeight: "bold", fontSize: 12, color: "#7fa89f" }}>PERGUNTA DO INTERVIEWER: </span>
                    </div>

                </div>
                <div style={style.barraInferior}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
                        <p style={{ fontFamily: "DM Sans", fontSize: 13, color: "#7fa89f", margin: 0 }}>
                            {turno === "interviewer" ? "O entrevistador está falando…" : "Sua vez de responder"}
                        </p>

                        <div style={{ display: "flex", position: "relative", flexDirection: "row", alignItems: "center", justifyContent: "center" }}>
                            <button
                                onClick={gravando ? pararGravacao : comecarGravacao}
                                disabled={turno !== "voce"}
                                style={{
                                    ...style.microphone,
                                    transform: gravando ? "scale(1.1)" : "scale(1)",
                                    backgroundColor: gravando ? "#688b84" : "#7fa89f",
                                    opacity: turno === "voce" ? 1 : 0.4,
                                    cursor: turno === "voce" ? "pointer" : "default",
                                }}
                            >
                                {gravando ? (
                                    <Square size={24} color="#ffffff" fill="#ffffff" />
                                ) : (
                                    <Mic size={24} color="#ffffff" />
                                )}
                            </button>
                            <button style={style.teclado}>
                                <Keyboard size={24} color="#7fa89f" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

        </Layout>
    );
}



const style = {


    etapa: {
        width: "100%",
        maxWidth: 900,
        height: 60,
        backgroundColor: "#ffffff",
        borderRadius: 18,
        border: "1px solid #d1e9e4",

    },
    painel: {
        alignItems: "center",
        textAlign: "center",
        flexDirection: "column",
        display: "flex",
        borderRadius: 18,
        maxWidth: 900,
        backgroundColor: "#ffffff",
        height: 520,
        boxShadow: "0px 4px 12px rgba(0, 0, 0, 0.1)",
        width: "100%",
        border: "1px solid #d1e9e4",
    },

    pergunta: {
        width: "100%",
        maxWidth: 700,
        marginTop: 40,
        height: "auto",
        minHeight: 140,
        backgroundColor: "#f1faf8",
        border: "1px solid #d1e9e4",
        borderRadius: 12,
        boxSizing: "border-box",
    },
    barraInferior: {
        width: "100%",
        maxWidth: 900,
        height: 80,
        display: "flex",
        backgroundColor: "#ffffff",
        borderRadius: 18,
        border: "1px solid #d1e9e4",
        display: "flex",
        alignItems: "center",
        boxShadow: "0px 4px 12px rgba(0, 0, 0, 0.1)",
        justifyContent: "center",
    },
    microphone: {
        width: 190,
        height: 40,

        borderRadius: 15,
        boxShadow: "0px 6px 8px rgba(34, 34, 34, 0.15)",
        border: "none",
        transition: "all 0.2s",

    },
    teclado: {
        width: 60,
        height: 40,
        marginLeft: 20,
        borderRadius: 15,
        boxShadow: "0px 4px 12px rgba(0, 0, 0, 0.1)",
        border: "none",
        left: "calc(50% + 90px)",
        position: "absolute",
        backgroundColor: "#ffffff",
    },
};