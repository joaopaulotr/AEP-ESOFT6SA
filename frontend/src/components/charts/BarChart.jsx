import { useId, useState } from "react";
import DataTable from "./DataTable";

const NUM = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

function resumo(titulo, dados, formatar) {
    if (!dados.length) return `${titulo}: sem dados.`;
    const top = [...dados].sort((a, b) => b.valor - a.valor).slice(0, 3)
        .map((d) => `${d.rotulo} ${formatar(d.valor)}`).join("; ");
    return `${titulo}. ${dados.length} ${dados.length === 1 ? "item" : "itens"}. Maiores valores: ${top}.`;
}

function Moldura({ titulo, dados, formatar, rotuloValor, children }) {
    const [aberto, setAberto] = useState(false);
    const id = useId();
    return (
        <figure style={{ margin: 0, backgroundColor: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 20, padding: 16, minWidth: 0 }}>
            <figcaption style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                <h3 style={{ margin: 0, fontSize: 16, color: "var(--color-heading)", fontFamily: "var(--font-heading)" }}>{titulo}</h3>
                {dados.length > 0 && (
                    <button className="ui-btn" aria-expanded={aberto} aria-controls={id} onClick={() => setAberto((v) => !v)}
                        style={{ minHeight: "var(--touch-target)", padding: "0 12px", borderRadius: 12, border: "1px solid var(--color-primary-border)", background: "none", color: "var(--color-primary)", fontWeight: 600, fontSize: 13.5, cursor: "pointer", fontFamily: "var(--font-sans)" }}>
                        {aberto ? "Ocultar dados" : "Ver dados"}
                    </button>
                )}
            </figcaption>
            {dados.length === 0
                ? <p style={{ margin: 0, fontSize: 14, color: "var(--color-text-muted)" }}>Sem dados ainda.</p>
                : children}
            <div id={id} hidden={!aberto}>
                {aberto && <DataTable legenda={titulo} colunas={["Item", rotuloValor]} linhas={dados.map((d) => [d.rotulo, formatar(d.valor)])} />}
            </div>
        </figure>
    );
}

/** Barras horizontais com valor ao lado de cada barra (rotulagem direta). */
export function BarChart({ titulo, dados, formatar = (v) => NUM.format(v), cor = "var(--chart-1)", rotuloValor = "Valor" }) {
    const max = Math.max(...dados.map((d) => d.valor), 0) || 1;
    const alturaLinha = 34;
    return (
        <Moldura titulo={titulo} dados={dados} formatar={formatar} rotuloValor={rotuloValor}>
            <div role="img" aria-label={resumo(titulo, dados, formatar)} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {dados.map((d, i) => (
                    <div key={i} aria-hidden="true" style={{ display: "grid", gridTemplateColumns: "minmax(70px, 38%) 1fr", gap: 10, alignItems: "center" }}>
                        <span title={d.rotulo} style={{ fontSize: 13.5, color: "var(--color-text)", overflowWrap: "anywhere", lineHeight: 1.3 }}>{d.rotulo}</span>
                        <svg width="100%" height={alturaLinha} style={{ display: "block" }}>
                            <rect x="0" y="6" height={alturaLinha - 12} rx="4" fill={cor}
                                width={`${Math.max((d.valor / max) * 80, d.valor > 0 ? 0.8 : 0)}%`} />
                            <text y={alturaLinha / 2 + 5} x={`${Math.max((d.valor / max) * 80, d.valor > 0 ? 0.8 : 0)}%`} dx="6" fontSize="13" fontWeight="600" fill="var(--color-heading)">{formatar(d.valor)}</text>
                        </svg>
                    </div>
                ))}
            </div>
        </Moldura>
    );
}

/** Colunas verticais (série temporal curta); rótulo do eixo = dd/MM. */
export function ColumnChart({ titulo, dados: todos = [], formatar = (v) => NUM.format(v), cor = "var(--chart-1)", rotuloValor = "Valor" }) {
    const dados = todos.slice(-30); // últimos 30 pontos
    const cortou = todos.length > dados.length;
    const max = Math.max(...dados.map((d) => d.valor), 0) || 1;
    const altura = 150;
    const largura = Math.max(dados.length * 44, 240);
    const w = 28;
    return (
        <Moldura titulo={titulo} dados={dados} formatar={formatar} rotuloValor={rotuloValor}>
            <div role="region" tabIndex={0} aria-label={`${titulo || "Gráfico"} — role para ver mais`} style={{ overflowX: "auto" }}>
                <svg role="img" aria-label={resumo(titulo, dados, formatar)} width={largura} height={altura + 40} viewBox={`0 0 ${largura} ${altura + 40}`} style={{ display: "block", maxWidth: "none" }}>
                    <line x1="0" x2={largura} y1={altura + 18} y2={altura + 18} stroke="var(--color-divider)" />
                    {dados.map((d, i) => {
                        const h = (d.valor / max) * altura;
                        const x = i * 44 + (44 - w) / 2;
                        return (
                            <g key={i} aria-hidden="true">
                                <rect x={x} y={altura + 18 - h} width={w} height={h} rx="3" fill={cor} />
                                <text x={x + w / 2} y={altura + 18 - h - 5} textAnchor="middle" fontSize="12" fontWeight="600" fill="var(--color-heading)">{formatar(d.valor)}</text>
                                <text x={x + w / 2} y={altura + 34} textAnchor="middle" fontSize="12" fill="var(--color-text-muted)">{d.rotulo}</text>
                            </g>
                        );
                    })}
                </svg>
            </div>
            {cortou && <p style={{ margin: "8px 0 0", fontSize: 13, color: "var(--color-text-muted)" }}>Mostrando os últimos 30 dias com entrevistas</p>}
        </Moldura>
    );
}

export default BarChart;
