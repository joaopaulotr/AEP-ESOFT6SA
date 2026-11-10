import { useState } from "react";
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

                <label style={style.label} htmlFor="login-email">E-mail</label>
                <div style={style.field}>
                    <Mail size={18} style={{ color: "var(--color-icon)" }} aria-hidden="true" />
                    <input
                        style={style.input}
                        id="login-email"
                        type="email"
                        autoComplete="email"
                        placeholder="voce@email.com"
                        value={email}
                        onChange={(e) => { setEmail(e.target.value); setErro(""); }}
                    />
                </div>

                <label style={style.label} htmlFor="login-senha">Senha</label>
                <div style={style.field}>
                    <Lock size={18} style={{ color: "var(--color-icon)" }} aria-hidden="true" />
                    <input
                        style={style.input}
                        id="login-senha"
                        type="password"
                        autoComplete="current-password"
                        placeholder="••••••••"
                        value={senha}
                        onChange={(e) => { setSenha(e.target.value); setErro(""); }}
                        onKeyDown={(e) => e.key === "Enter" && entrar()}
                    />
                </div>

                <div style={style.forgotRow}>
                    <span style={style.link}>Esqueci a senha</span>
                </div>

                {erro && <div style={style.erro} role="alert">{erro}</div>}

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
        <svg width="17" height="17" viewBox="0 0 48 48" aria-hidden="true">
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
        backgroundColor: "var(--color-surface)",
        borderRadius: 18,
        padding: "clamp(22px, 6vw, 34px)",
        textAlign: "center",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        boxShadow: "var(--shadow-card)",
    },
    badge: {
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        marginTop: 14,
        padding: "5px 11px",
        borderRadius: 999,
        fontFamily: "var(--font-sans)",
        fontSize: 12.5,
        fontWeight: 600,
        color: "var(--color-primary)",
        backgroundColor: "var(--color-accent-soft)",
    },
    title: {
        fontFamily: "var(--font-heading)",
        fontWeight: 800,
        fontSize: 24,
        marginTop: 14,
        marginBottom: 0,
        color: "var(--color-heading)",
    },
    subtitle: {
        fontFamily: "var(--font-sans)",
        fontSize: 14,
        color: "var(--color-text-muted)",
        marginTop: 6,
        marginBottom: 22,
    },
    label: {
        width: "100%",
        textAlign: "left",
        fontFamily: "var(--font-sans)",
        fontSize: 13,
        fontWeight: 600,
        color: "var(--color-text-muted)",
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
        border: "1px solid var(--color-border-soft)",
        borderRadius: 18,
        backgroundColor: "var(--color-input-bg)",
        boxSizing: "border-box",
    },
    input: {
        flex: 1,
        border: "none",
        outline: "none",
        background: "none",
        fontFamily: "var(--font-sans)",
        fontSize: 15,
        color: "var(--color-text)",
        minWidth: 0,
    },
    forgotRow: {
        width: "100%",
        display: "flex",
        justifyContent: "flex-end",
        marginBottom: 6,
    },
    link: {
        fontFamily: "var(--font-sans)",
        fontSize: 13,
        fontWeight: 600,
        color: "var(--color-primary)",
        cursor: "pointer",
    },
    erro: {
        width: "100%",
        textAlign: "left",
        color: "var(--color-error)",
        fontFamily: "var(--font-sans)",
        fontSize: 13,
        fontWeight: 600,
        marginBottom: 6,
    },
    entrarBtn: {
        width: "100%",
        height: "var(--touch-target)",
        marginTop: 6,
        backgroundColor: "var(--color-primary)",
        borderRadius: 18,
        border: "none",
        color: "var(--color-on-primary)",
        fontFamily: "var(--font-sans)",
        fontWeight: 600,
        fontSize: 15,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 9,
        cursor: "pointer",
        boxShadow: "var(--shadow-button)",
    },
    divider: {
        width: "100%",
        display: "flex",
        alignItems: "center",
        gap: 12,
        color: "var(--color-text-muted)",
        fontFamily: "var(--font-sans)",
        fontSize: 13,
        margin: "16px 0",
    },
    googleBtn: {
        width: "100%",
        height: 45,
        backgroundColor: "var(--color-surface)",
        borderRadius: 18,
        border: "1px solid var(--color-border-soft)",
        color: "var(--color-primary)",
        fontFamily: "var(--font-sans)",
        fontWeight: 600,
        fontSize: 15,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 9,
        cursor: "pointer",
    },
    footer: {
        fontFamily: "var(--font-sans)",
        fontSize: 13.5,
        color: "var(--color-text-muted)",
        marginTop: 16,
        marginBottom: 0,
    },
};