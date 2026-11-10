import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles, RefreshCw, Info } from "lucide-react";
import EstadoTela from "./EstadoTela";
import { useApiResource } from "../hooks/useApiResource";
import { api, ApiError } from "../services/api";
import { dataHora } from "../utils/tempo";
import { ui } from "../styles/ui";

const H3 = { margin: "0 0 6px", fontSize: 16, color: "var(--color-heading)" };
const LISTA = { margin: 0, paddingLeft: 20, fontSize: 15, lineHeight: 1.55, color: "var(--color-text)" };
const ALERTA = { margin: 0, color: "var(--color-error)", fontSize: 14 };
const SR = { position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)", whiteSpace: "nowrap" };

function Lista({ titulo, itens }) {
    if (!itens?.length) return null;
    return (
        <div>
            <h3 style={H3}>{titulo}</h3>
            <ul style={LISTA}>{itens.map((t, i) => <li key={i}>{t}</li>)}</ul>
        </div>
    );
}

/** Relatório cruzado do roteiro (EV-33): resumo, temas com citações linkadas, divergências e lacunas. */
export default function ScriptSynthesis({ scriptId, concluidas = null }) {
    const { data, carregando, erro, recarregar } = useApiResource(() => api.getScriptSynthesis(scriptId), [scriptId]);
    const [gerando, setGerando] = useState(false);
    const [erroGerar, setErroGerar] = useState("");
    const [bloqueio, setBloqueio] = useState("");
    const [falhas, setFalhas] = useState(0);
    const alertaRef = useRef(null);
    const mensagemErro = bloqueio || erroGerar;
    useEffect(() => { if (mensagemErro) alertaRef.current?.focus(); }, [mensagemErro, falhas]);
    const poucas = concluidas !== null && concluidas < 2;

    async function gerar(refresh) {
        if (refresh && !window.confirm("Gerar o relatório de novo? O atual será substituído.")) return;
        setGerando(true);
        setBloqueio("");
        setErroGerar("");
        try {
            await api.generateScriptSynthesis(scriptId, { refresh });
            setBloqueio("");
            setErroGerar("");
            await recarregar();
        } catch (e) {
            setFalhas((n) => n + 1);
            if (e instanceof ApiError && e.status === 409) { setBloqueio(e.detail); setErroGerar(""); }
            else setErroGerar(e.detail || "Não consegui gerar o relatório. Tente de novo.");
        } finally {
            setGerando(false);
        }
    }

    return (
        <section style={{ ...ui.card, marginTop: 20 }} aria-labelledby="titulo-relatorio">
            <h2 id="titulo-relatorio" style={{ margin: "0 0 14px", fontSize: 18, color: "var(--color-heading)", fontFamily: "var(--font-heading)" }}>Relatório do roteiro</h2>
            <EstadoTela carregando={carregando} erro={erro} onRetry={recarregar} data={data}>
                {data ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                        <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6, color: "var(--color-text)", whiteSpace: "pre-line" }}>{data.resumo}</p>
                        {(data.temas ?? []).map((t, i) => (
                            <div key={i}>
                                <h3 style={H3}>{t.tema}</h3>
                                {t.pontos?.length > 0 && <ul style={{ ...LISTA, marginBottom: 8 }}>{t.pontos.map((p, j) => <li key={j}>{p}</li>)}</ul>}
                                {t.citacoes?.map((c, j) => (
                                    <blockquote key={j} style={{ margin: "8px 0", padding: "8px 14px", borderLeft: "4px solid var(--color-primary-border)", backgroundColor: "var(--color-accent-soft)", borderRadius: "0 12px 12px 0", fontSize: 15, fontStyle: "italic", lineHeight: 1.5, color: "var(--color-text)" }}>
                                        “{c.texto}”{" "}
                                        <Link to={`/sessao/${encodeURIComponent(c.session_id)}`} style={{ fontStyle: "normal", fontSize: 13.5, color: "var(--color-primary)", fontWeight: 600 }}>
                                            Ver entrevista<span style={SR}> desta citação</span>
                                        </Link>
                                    </blockquote>
                                ))}
                            </div>
                        ))}
                        <Lista titulo="Divergências entre entrevistas" itens={data.divergencias} />
                        <Lista titulo="O que ficou sem resposta" itens={data.lacunas} />
                        <p style={{ ...ui.meta, margin: 0 }}>
                            Baseado em {data.sessoes_usadas?.length ?? 0} entrevistas{data.updated_at ? ` · gerado em ${dataHora(data.updated_at)}` : ""}
                        </p>
                        <div>
                            <button className="ui-btn" style={{ ...ui.btnSecundario, opacity: gerando ? 0.6 : 1 }} onClick={() => gerar(true)} disabled={gerando}>
                                <RefreshCw size={16} aria-hidden="true" /> {gerando ? "Gerando…" : "Gerar de novo"}
                            </button>
                        </div>
                        {mensagemErro && <p role="alert" ref={alertaRef} tabIndex={-1} style={ALERTA}>{mensagemErro}</p>}
                    </div>
                ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "flex-start" }}>
                        <p style={{ margin: 0, fontSize: 15, color: "var(--color-text-muted)" }}>O relatório cruzado deste roteiro ainda não foi gerado.</p>
                        <button className="ui-btn" style={{ ...ui.btnPrimario, opacity: gerando ? 0.6 : 1 }} onClick={() => gerar(false)} disabled={gerando}>
                            <Sparkles size={17} aria-hidden="true" /> {gerando ? "Gerando… pode levar alguns segundos" : "Gerar relatório"}
                        </button>
                        {poucas && !mensagemErro && (
                            <p style={{ margin: 0, fontSize: 14, color: "var(--color-text)", display: "flex", gap: 8, alignItems: "center" }}>
                                <Info size={16} aria-hidden="true" /> Para gerar o relatório, é preciso ter pelo menos 2 entrevistas concluídas com síntese.
                            </p>
                        )}
                        {mensagemErro && <p role="alert" ref={alertaRef} tabIndex={-1} style={ALERTA}>{mensagemErro}</p>}
                    </div>
                )}
            </EstadoTela>
        </section>
    );
}
