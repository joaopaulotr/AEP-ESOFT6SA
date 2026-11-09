// Estilos compartilhados das telas de roteiros, sessões e detalhe.
export const CSS = `
.girando{animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.ui-btn:focus-visible,.ui-card-link:focus-visible{outline:3px solid var(--color-focus);outline-offset:2px}
`;

export const ui = {
    page: { width: "100%", maxWidth: 980, margin: "0 auto", fontFamily: "var(--font-sans)", boxSizing: "border-box" },
    h1: { margin: 0, fontFamily: "var(--font-heading)", fontSize: "clamp(22px, 5vw, 30px)", color: "var(--color-heading)", letterSpacing: "-0.02em" },
    sub: { margin: "6px 0 0", fontSize: 14.5, color: "var(--color-text-muted)", lineHeight: 1.5 },
    topo: { display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-start", justifyContent: "space-between", marginBottom: 20 },
    voltar: { display: "inline-flex", alignItems: "center", gap: 6, marginBottom: 14, padding: "8px 4px", minHeight: "var(--touch-target)", background: "none", border: "none", color: "var(--color-primary)", fontWeight: 600, fontSize: 14, cursor: "pointer", fontFamily: "var(--font-sans)" },
    card: { backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 20, padding: 18, boxSizing: "border-box" },
    btnPrimario: { display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8, minHeight: "var(--touch-target)", padding: "0 18px", borderRadius: 16, border: "none", backgroundColor: "var(--color-primary)", color: "var(--color-on-primary)", fontWeight: 600, fontSize: 14.5, cursor: "pointer", fontFamily: "var(--font-sans)", boxShadow: "var(--shadow-button)" },
    btnSecundario: { display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8, minHeight: "var(--touch-target)", padding: "0 16px", borderRadius: 16, border: "1px solid var(--color-primary-border)", backgroundColor: "var(--color-surface)", color: "var(--color-primary)", fontWeight: 600, fontSize: 14.5, cursor: "pointer", fontFamily: "var(--font-sans)" },
    btnPerigo: { display: "inline-flex", alignItems: "center", gap: 6, minHeight: "var(--touch-target)", padding: "0 12px", borderRadius: 12, border: "none", background: "none", color: "var(--color-danger)", fontWeight: 600, fontSize: 13.5, cursor: "pointer", fontFamily: "var(--font-sans)" },
    estado: { display: "flex", flexDirection: "column", alignItems: "center", gap: 12, padding: "48px 16px", textAlign: "center", color: "var(--color-text-muted)" },
    estadoTexto: { margin: 0, fontSize: 15, lineHeight: 1.5 },
    meta: { fontSize: 13.5, color: "var(--color-text-muted)" },
};
