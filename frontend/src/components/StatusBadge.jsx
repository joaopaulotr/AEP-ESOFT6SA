const ROTULOS = {
    concluida: { texto: "Concluída", cor: "var(--color-primary)", fundo: "var(--color-accent-soft)", borda: "var(--color-accent-soft-border)" },
    em_andamento: { texto: "Em andamento", cor: "var(--color-thinking)", fundo: "var(--color-surface-2)", borda: "var(--color-border)" },
};

export default function StatusBadge({ status }) {
    const r = ROTULOS[status] ?? ROTULOS.em_andamento;
    return (
        <span style={{
            display: "inline-block",
            padding: "3px 10px",
            borderRadius: 999,
            fontSize: 12.5,
            fontWeight: 700,
            fontFamily: "var(--font-sans)",
            color: r.cor,
            backgroundColor: r.fundo,
            border: `1px solid ${r.borda}`,
            whiteSpace: "nowrap",
        }}>{r.texto}</span>
    );
}
