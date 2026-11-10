import { useEffect, useRef, useState } from "react";
import { Copy, ExternalLink, X } from "lucide-react";
import { api } from "../services/api";
import { ui, CSS } from "../styles/ui";

async function copiarTexto(texto) {
    try {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(texto);
            return true;
        }
    } catch { /* cai no fallback */ }
    try {
        const area = document.createElement("textarea");
        area.value = texto;
        area.setAttribute("readonly", "");
        area.style.position = "fixed";
        area.style.opacity = "0";
        document.body.appendChild(area);
        area.select();
        const ok = document.execCommand("copy");
        document.body.removeChild(area);
        return ok;
    } catch {
        return false;
    }
}

const FOCAVEIS = 'button, a[href], input, [tabindex]:not([tabindex="-1"])';

/** Diálogo com o link do convite, botão de copiar, QR Code e atalho para abrir. */
export default function InviteModal({ roteiro, onClose }) {
    const dialogRef = useRef(null);
    const [aviso, setAviso] = useState("");
    const [qrFalhou, setQrFalhou] = useState(false);
    const link = roteiro.link_convite;
    const onCloseRef = useRef(onClose);
    onCloseRef.current = onClose;

    useEffect(() => {
        const aberto = document.activeElement;
        dialogRef.current?.querySelector("button")?.focus();
        function aoTeclar(e) {
            if (e.key === "Escape") { e.stopPropagation(); onCloseRef.current(); return; }
            if (e.key !== "Tab") return;
            const itens = [...dialogRef.current.querySelectorAll(FOCAVEIS)].filter((el) => !el.disabled);
            if (itens.length === 0) return;
            const primeiro = itens[0];
            const ultimo = itens[itens.length - 1];
            if (e.shiftKey && document.activeElement === primeiro) { e.preventDefault(); ultimo.focus(); }
            else if (!e.shiftKey && document.activeElement === ultimo) { e.preventDefault(); primeiro.focus(); }
        }
        document.addEventListener("keydown", aoTeclar);
        return () => {
            document.removeEventListener("keydown", aoTeclar);
            aberto?.focus?.();
        };
    }, []);

    async function copiar() {
        const ok = await copiarTexto(link);
        setAviso(ok ? "Link copiado!" : "Não consegui copiar. Selecione o link e copie à mão.");
    }

    return (
        <div
            onClick={(e) => { if (e.target === e.currentTarget) onCloseRef.current(); }}
            style={{ position: "fixed", inset: 0, zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: 16, backgroundColor: "rgba(0,0,0,0.5)" }}
        >
            <style>{CSS}</style>
            <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="convite-titulo"
                style={{ ...ui.card, width: "100%", maxWidth: 420, maxHeight: "100%", overflowY: "auto", display: "flex", flexDirection: "column", gap: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                    <h2 id="convite-titulo" style={{ margin: 0, fontSize: 19, color: "var(--color-heading)", fontFamily: "var(--font-heading)" }}>
                        Convidar para “{roteiro.titulo}”
                    </h2>
                    <button className="ui-btn" style={{ ...ui.btnSecundario, padding: "0 12px" }} onClick={onClose} aria-label="Fechar">
                        <X size={18} aria-hidden="true" />
                    </button>
                </div>
                <p style={{ margin: 0, fontSize: 14, color: "var(--color-text-2)" }}>
                    Quem receber este link pode responder sem criar conta.
                </p>
                <p style={{ margin: 0, padding: "10px 12px", borderRadius: 12, border: "1px solid var(--color-border)", backgroundColor: "var(--color-input-bg)", color: "var(--color-text)", fontSize: 14, wordBreak: "break-all" }}>
                    {link}
                </p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                    <button className="ui-btn" style={ui.btnPrimario} onClick={copiar}>
                        <Copy size={17} aria-hidden="true" /> Copiar link
                    </button>
                    <a className="ui-btn" style={{ ...ui.btnSecundario, textDecoration: "none" }} href={link} target="_blank" rel="noopener noreferrer">
                        <ExternalLink size={17} aria-hidden="true" /> Abrir convite
                    </a>
                </div>
                <p role="status" aria-live="polite" style={{ margin: 0, minHeight: 20, fontSize: 14, color: "var(--color-primary)", fontWeight: 600 }}>{aviso}</p>
                {qrFalhou ? (
                    <p role="status" style={{ margin: 0, textAlign: "center", fontSize: 14, color: "var(--color-text-muted)" }}>
                        Não consegui carregar o QR; use o link acima.
                    </p>
                ) : (
                    <img src={api.qrCodeUrl(roteiro.script_id)} alt={`QR code do convite para ${roteiro.titulo}`}
                        width={200} height={200} onError={() => setQrFalhou(true)}
                        style={{ alignSelf: "center", backgroundColor: "#fff", padding: 8, borderRadius: 12, border: "1px solid var(--color-border)" }} />
                )}
            </div>
        </div>
    );
}
