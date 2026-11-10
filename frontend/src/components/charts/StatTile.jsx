
export default function StatTile({ rotulo, valor, detalhe }) {
    return (
        <div style={{ backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 20, padding: 16, display: "flex", flexDirection: "column", gap: 4, minWidth: 0 }}>
            <span style={{ fontSize: 13.5, color: "var(--color-text-muted)" }}>{rotulo}</span>
            <strong style={{ fontSize: "clamp(22px, 5vw, 28px)", color: "var(--color-heading)", fontFamily: "var(--font-heading)" }}>{valor}</strong>
            {detalhe && <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{detalhe}</span>}
        </div>
    );
}
