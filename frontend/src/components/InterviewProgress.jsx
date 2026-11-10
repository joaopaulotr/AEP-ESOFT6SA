import React from "react";

/** "Pergunta 2 de 5 · aprofundando". Some se a ordem ou o total ainda não são conhecidos. */
export function textoProgresso({ ordem, total, acao }) {
    if (!ordem || !total) return "";
    return `Pergunta ${ordem} de ${total}${acao === "deepen" ? " · aprofundando" : ""}`;
}

export default function InterviewProgress({ ordem, total, acao }) {
    const texto = textoProgresso({ ordem, total, acao });
    if (!texto) return null;
    const pct = Math.min(100, Math.round((ordem / total) * 100));
    return (
        <div style={s.wrap}>
            <span style={s.texto}>{texto}</span>
            <div
                role="progressbar"
                aria-label="Progresso da entrevista"
                aria-valuemin={0}
                aria-valuemax={total}
                aria-valuenow={Math.min(ordem, total)}
                aria-valuetext={texto}
                style={s.trilho}
            >
                <div style={{ ...s.barra, width: `${pct}%` }} />
            </div>
        </div>
    );
}

const s = {
    wrap: { width: "100%", display: "flex", flexDirection: "column", gap: 6 },
    texto: { fontSize: 13, fontWeight: 700, color: "var(--color-text)" },
    trilho: { height: 6, borderRadius: 99, background: "var(--color-surface-2)", overflow: "hidden" },
    barra: { height: "100%", borderRadius: 99, background: "var(--color-primary)", transition: "width .4s ease" },
};
