import { useState } from "react";
import React from "react";
import Avatar from "../components/Avatar";
import Layout from "../components/Layout";
import { useNavigate } from "react-router-dom";
import { Mail, Lock, ArrowRight, Sparkles } from "lucide-react";

export default function LoginScreen() {
    const navigate = useNavigate();
    const [email, setEmail] = useState("");
    const [senha, setSenha] = useState("");
    const [erro, setErro] = useState("");

    function entrar() {
        if (!email.trim() || !senha.trim()) {
            setErro("Preencha e-mail e senha para continuar.");
            return;
        }
        navigate("/welcome"); 
    }

    return (
        <Layout>
            <style>{FONTS}</style>
            <div style={style.card}>
                <Avatar size={92} />

                <div style={style.badge}>
                    <Sparkles size={12} /> Du
                </div>

                <h1 style={style.title}>Bem vindo de volta!</h1>
                <p style={style.subtitle}>Entre para fazer entrevistas com a Interviewer.</p>

                <label style={style.label}>E-mail</label>
                <div style={style.field}>
                    <Mail size={18} color="#8aa39c" />
                    <input
                        style={style.input}
                        type="email"
                        placeholder="voce@email.com"
                        value={email}
                        onChange={(e) => { setEmail(e.target.value); setErro(""); }}
                    />
                </div>

                <label style={style.label}>Senha</label>
                <div style={style.field}>
                    <Lock size={18} color="#8aa39c" />
                    <input
                        style={style.input}
                        type="password"
                        placeholder="••••••••"
                        value={senha}
                        onChange={(e) => { setSenha(e.target.value); setErro(""); }}
                        onKeyDown={(e) => e.key === "Enter" && entrar()}
                    />
                </div>

                <div style={style.forgotRow}>
                    <span style={style.link}>Esqueci a senha</span>
                </div>

                {erro && <div style={style.erro}>{erro}</div>}

                <button style={style.entrarBtn} onClick={entrar}>
                    Entrar <ArrowRight size={18} />
                </button>

                <div style={style.divider}>ou</div>

                <button style={style.googleBtn} onClick={() => navigate("/welcome")}>
                    <GoogleG /> Continuar com Google
                </button>

                <p style={style.footer}>
                    Ainda não tem conta? <span style={style.link}>Criar conta</span>
                </p>
            </div>
        </Layout>
    );
}

function GoogleG() {
    return (
        <svg width="17" height="17" viewBox="0 0 48 48">
            <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.6l6.7-6.7C35.6 2.4 30.2 0 24 0 14.6 0 6.4 5.4 2.6 13.3l7.8 6.1C12.3 13.2 17.6 9.5 24 9.5z" />
            <path fill="#4285F4" d="M46.1 24.6c0-1.6-.1-2.8-.4-4.1H24v7.8h12.5c-.3 2.1-1.6 5.2-4.6 7.3l7.1 5.5c4.2-3.9 6.7-9.6 6.7-16.5z" />
            <path fill="#FBBC05" d="M10.4 28.6c-.5-1.5-.8-3-.8-4.6s.3-3.1.8-4.6l-7.8-6.1C1 16.3 0 20 0 24s1 7.7 2.6 10.7l7.8-6.1z" />
            <path fill="#34A853" d="M24 48c6.2 0 11.4-2 15.2-5.5l-7.1-5.5c-2 1.3-4.6 2.3-8.1 2.3-6.4 0-11.7-3.7-13.6-9.9l-7.8 6.1C6.4 42.6 14.6 48 24 48z" />
        </svg>
    );
}

const FONTS = `
@import url('https://fonts.googleapis.com/css2?family=Coiny&family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=Lexend:wght@700&family=Momo+Trust+Display&family=Momo+Trust+Sans:wght@200..800&family=Paytone+One&family=Silkscreen:wght@400;700&display=swap');`;

const style = {
    card: {
        width: 420,
        maxWidth: "100%",
        backgroundColor: "white",
        borderRadius: 18,
        padding: 34,
        textAlign: "center",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        boxShadow: "0 12px 40px #2A262212, 0 2px 6px #2A26220A",
    },
    badge: {
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        marginTop: 14,
        padding: "5px 11px",
        borderRadius: 999,
        fontFamily: "dm sans",
        fontSize: 12.5,
        fontWeight: 600,
        color: "#4f776e",
        backgroundColor: "#e9f3f0",
    },
    title: {
        fontFamily: "Momo Trust Sans",
        fontWeight: 800,
        fontSize: 24,
        marginTop: 14,
        marginBottom: 0,
        color: "#1f2d29",
    },
    subtitle: {
        fontFamily: "dm sans",
        fontSize: 14,
        color: "#6a7d77",
        marginTop: 6,
        marginBottom: 22,
    },
    label: {
        width: "100%",
        textAlign: "left",
        fontFamily: "dm sans",
        fontSize: 13,
        fontWeight: 600,
        color: "#6a7d77",
        marginBottom: 6,
        marginTop: 4,
    },
    field: {
        width: "100%",
        height: 45,
        marginBottom: 12,
        padding: "0 14px",
        display: "flex",
        alignItems: "center",
        gap: 10,
        border: "1px solid #d1e9e4",
        borderRadius: 18,
        backgroundColor: "#fbfdfc",
        boxSizing: "border-box",
    },
    input: {
        flex: 1,
        border: "none",
        outline: "none",
        background: "none",
        fontFamily: "dm sans",
        fontSize: 15,
        color: "#2f3e3a",
    },
    forgotRow: {
        width: "100%",
        display: "flex",
        justifyContent: "flex-end",
        marginBottom: 6,
    },
    link: {
        fontFamily: "dm sans",
        fontSize: 13,
        fontWeight: 600,
        color: "#4f776e",
        cursor: "pointer",
    },
    erro: {
        width: "100%",
        textAlign: "left",
        color: "#c9563b",
        fontFamily: "dm sans",
        fontSize: 13,
        fontWeight: 600,
        marginBottom: 6,
    },
    entrarBtn: {
        width: "100%",
        height: 40,
        marginTop: 6,
        backgroundColor: "#4f776e",
        borderRadius: 18,
        border: "none",
        color: "white",
        fontFamily: "dm sans",
        fontWeight: 600,
        fontSize: 15,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 9,
        cursor: "pointer",
        boxShadow: "0 8px 22px -16px rgba(31,45,41,.6)",
    },
    divider: {
        width: "100%",
        display: "flex",
        alignItems: "center",
        gap: 12,
        color: "#9db3ac",
        fontFamily: "dm sans",
        fontSize: 13,
        margin: "16px 0",
    },
    googleBtn: {
        width: "100%",
        height: 45,
        backgroundColor: "#ffffff",
        borderRadius: 18,
        border: "1px solid #d1e9e4",
        color: "#4f776e",
        fontFamily: "dm sans",
        fontWeight: 600,
        fontSize: 15,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 9,
        cursor: "pointer",
    },
    footer: {
        fontFamily: "dm sans",
        fontSize: 13.5,
        color: "#6a7d77",
        marginTop: 16,
        marginBottom: 0,
    },
};