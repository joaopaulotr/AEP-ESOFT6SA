
/** Tabela de dados de um gráfico (alternativa textual, aberta por "Ver dados"). */
export default function DataTable({ legenda, colunas, linhas }) {
    return (
        <div style={{ overflowX: "auto", marginTop: 10 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14, color: "var(--color-text)" }}>
                <caption style={{ textAlign: "left", fontSize: 13, color: "var(--color-text-muted)", paddingBottom: 6 }}>{legenda}</caption>
                <thead>
                    <tr>
                        {colunas.map((c, i) => (
                            <th key={c} scope="col" style={{ textAlign: i === 0 ? "left" : "right", padding: "6px 8px", borderBottom: "1px solid var(--color-divider)", color: "var(--color-heading)" }}>{c}</th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {linhas.map((l, i) => (
                        <tr key={i}>
                            {l.map((v, j) => (
                                <td key={j} style={{ textAlign: j === 0 ? "left" : "right", padding: "6px 8px", borderBottom: "1px solid var(--color-border-soft)" }}>{v}</td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
