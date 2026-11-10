import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Home, Mic, ListChecks, LogOut, Sparkles } from "lucide-react";
import ThemeToggle from "./ThemeToggle";

const NOME = "duda";  
const EMAIL = "duda";

function useIsMobile(breakpoint = 860) {
    const [isMobile, setIsMobile] = useState(
        typeof window !== "undefined" && window.innerWidth <= breakpoint
    );
    useEffect(() => {
        const onResize = () => setIsMobile(window.innerWidth <= breakpoint);
        window.addEventListener("resize", onResize);
        return () => window.removeEventListener("resize", onResize);
    }, [breakpoint]);
    return isMobile;
}

export default function Sidebar({ children }) {
    const navigate = useNavigate();
    const location = useLocation();
    const isMobile = useIsMobile();    

    const itens = [
        { rota: "/welcome",    label: "Início",         icon: <Home size={19} /> },
        { rota: "/entrevistas", label: "Entrevistas",    icon: <ListChecks size={19} />, prefixos: ["/entrevistas", "/sessao"] },
        { rota: "/entrevista",  label: "Nova entrevista", icon: <Mic size={19} /> },
      
    ];

    return (
        <div style={style.root}>
            <style>{FONTS}</style>

            <aside style={{ ...style.rail, ...(isMobile ? style.railMobile : {}) }}>
                <div style={style.brand}>
                    <div style={style.brandMark}><Sparkles size={18} /></div>
                    {!isMobile && <span style={style.brandName}>du</span>}
                </div>

               <nav aria-label="Menu principal" style={{
    display: "flex",
    flexDirection: "column",
    gap: 4,
    flex: 1,
    alignItems: isMobile ? "center" : "stretch",
}}>
                    {itens.map((it) => {
                        const ativo = it.prefixos
                            ? it.prefixos.some((p) => location.pathname === p || location.pathname.startsWith(`${p}/`))
                            : location.pathname === it.rota;
                        return (
                            <button
                                key={it.rota}
                                onClick={() => navigate(it.rota)}
                                aria-current={ativo ? "page" : undefined}
                                aria-label={isMobile ? it.label : undefined}
                                style={{
                                    ...style.navItem,
                                    ...(ativo ? style.navItemActive : {}),
                                    width: isMobile ? "auto" : "100%",
                                    whiteSpace: "nowrap",
                                }}
                            >
                                {it.icon} {!isMobile && it.label}
                            </button>
                        );
                    })}
                </nav>

                <div style={{ display: "flex", justifyContent: isMobile ? "center" : "flex-start", padding: "0 4px 8px" }}>
                    <ThemeToggle />
                </div>

                <div style={{ ...style.railUser, ...(isMobile ? { marginLeft: "auto" } : {}) }}>
                    <div style={style.avatarMini}>{NOME.charAt(0).toUpperCase()}</div>
                    {!isMobile && (
                        <div style={{ flex: 1, minWidth: 0, textAlign: "left" }}>
                            <div style={style.userName}>{NOME}</div>
                            <div style={style.userEmail}>{EMAIL}</div>
                        </div>
                    )}
                    <button style={style.logout} title="Sair" aria-label="Sair" onClick={() => navigate("/")}>
                        <LogOut size={18} />
                    </button>
                </div>
            </aside>

            <main style={{ ...style.main, ...(isMobile ? { padding: "24px 16px 56px" } : {}) }}>
                {children}
            </main>
        </div>
    );
}

const FONTS = `
@import url('https://fonts.googleapis.com/css2?family=Coiny&family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=Lexend:wght@700&family=Momo+Trust+Display&family=Momo+Trust+Sans:wght@200..800&family=Paytone+One&family=Silkscreen:wght@400;700&display=swap');`;

const style = {
    root: {
        minHeight: "100vh",
        display: "flex",
        backgroundColor: "var(--color-bg)",
    },
    rail: {
        position: "sticky",
        top: 0,
        height: "100vh",
        width: 250,
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        gap: 6,
        padding: "22px 16px",
        backgroundColor: "var(--color-rail-bg)",
        backdropFilter: "blur(10px)",
        borderRight: "1px solid var(--color-border-soft)",
        boxSizing: "border-box",
    },
   railMobile: {
    width: 72,             
    padding: "22px 10px",
    alignItems: "center",  
},
    brand: {
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "8px 10px 18px",
    },
    brandMark: {
        width: 34,
        height: 34,
        borderRadius: 11,
        display: "grid",
        placeItems: "center",
        background: "linear-gradient(140deg,var(--color-primary-border),var(--color-primary))",
        color: "var(--color-on-primary)",
        boxShadow: "0 8px 18px -8px rgba(79,119,110,.7)",
    },
    brandName: {
        fontFamily: "var(--font-heading)",
        fontWeight: 700,
        fontSize: 20,
        color: "var(--color-heading)",
    },
    navItem: {
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "11px 12px",
        minHeight: "var(--touch-target)",
        borderRadius: 12,
        color: "var(--color-text-muted)",
        fontFamily: "var(--font-sans)",
        fontWeight: 600,
        fontSize: 14.5,
        cursor: "pointer",
        border: "none",
        background: "none",
        textAlign: "left",
        width: "100%",
    },
    navItemActive: {
        backgroundColor: "var(--color-primary)",
        color: "var(--color-on-primary)",
    },
    railUser: {
        display: "flex",
        alignItems: "center",
        gap: 11,
        padding: 10,
        borderRadius: 14,
        border: "1px solid var(--color-border-soft)",
        backgroundColor: "var(--color-surface)",
    },
    avatarMini: {
        width: 36,
        height: 36,
        borderRadius: "50%",
        background: "linear-gradient(135deg,#a9d0ec,#7fa89f)",
        display: "grid",
        placeItems: "center",
        color: "#fff",
        fontFamily: "var(--font-sans)",
        fontWeight: 700,
        fontSize: 14,
        flexShrink: 0,
    },
    userName: {
        fontFamily: "var(--font-sans)",
        fontWeight: 700,
        fontSize: 13.5,
        color: "var(--color-heading)",
        whiteSpace: "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis",
    },
    userEmail: {
        fontFamily: "var(--font-sans)",
        fontSize: 12,
        color: "var(--color-text-muted)",
        whiteSpace: "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis",
    },
    logout: {
        border: "none",
        background: "none",
        color: "var(--color-text-muted)",
        cursor: "pointer",
        padding: 8,
        minWidth: "var(--touch-target)",
        minHeight: "var(--touch-target)",
        borderRadius: 10,
        display: "grid",
        placeItems: "center",
    },
    main: {
        flex: 1,
        minWidth: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "40px 28px 64px",
    },
};