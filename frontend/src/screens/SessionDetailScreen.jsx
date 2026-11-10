import React, { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Trash2, Sparkles, Info } from "lucide-react";
import SideBar from "../components/SideBar";
import StatusBadge from "../components/StatusBadge";
import EstadoTela from "../components/EstadoTela";
import { useApiResource } from "../hooks/useApiResource";
import { api } from "../services/api";
import { dataHora } from "../utils/tempo";
import { ui, CSS } from "../styles/ui";

/** Texto longo → parágrafos (separados por linha em branco). */
function paragrafos(texto) {
    return (texto || "").split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);
}

function Transcricao({ turnos, perguntas, pessoa }) {
    const porOrdem = new Map((perguntas ?? []).map((p) => [p.ordem, p.texto]));
    let ordemAnterior;
    return (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {turnos.map((t, i) => {
                const souEu = t.role === "participant";
                const ordem = t.pergunta_ordem;
                const separador = ordem != null && ordem !== ordemAnterior && porOrdem.has(ordem);
                if (ordem != null) ordemAnterior = ordem;
                return (
                    <React.Fragment key={i}>
                        {separador && (
                            <p style={{ margin: "12px 0 2px", paddingTop: 12, borderTop: "1px solid var(--color-divider)", fontSize: 13.5, fontWeight: 700, color: "var(--color-primary)" }}>
                                Pergunta {ordem}: {porOrdem.get(ordem)}
                            </p>
                        )}
                        <div style={{ alignSelf: souEu ? "flex-end" : "flex-start", maxWidth: "min(560px, 88%)" }}>
                            <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginBottom: 3, textAlign: souEu ? "right" : "left" }}>
                                {souEu ? pessoa : "Entrevistadora"}
                            </div>
                            <div style={{
                                padding: "10px 14px", borderRadius: 16, fontSize: 15, lineHeight: 1.5, whiteSpace: "pre-wrap", overflowWrap: "anywhere",
                                color: souEu ? "var(--color-on-primary)" : "var(--color-text)",
                                backgroundColor: souEu ? "var(--color-primary)" : "var(--color-surface-2)",
                                border: souEu ? "none" : "1px solid var(--color-border)",
                            }}>{t.text}</div>
                        </div>
                    </React.Fragment>
                );
            })}
        </div>
    );
}

function Sintese({ sessionId, concluida }) {
    const { data, carregando, erro, recarregar } = useApiResource(() => api.getSynthesis(sessionId), [sessionId]);
    const [gerando, setGerando] = useState(false);
    const [erroGerar, setErroGerar] = useState("");

    async function gerar() {
        setGerando(true);
        setErroGerar("");
        try {
            await api.generateSynthesis(sessionId);
            await recarregar();
        } catch (e) {
            setErroGerar(e.detail || "Não consegui gerar a síntese. Tente de novo.");
        } finally {
            setGerando(false);
        }
    }

    return (
        <section style={{ ...ui.card, marginTop: 20 }} aria-labelledby="titulo-sintese">
            <h2 id="titulo-sintese" style={H2}>Síntese</h2>
            <EstadoTela carregando={carregando} erro={erro} onRetry={recarregar}>
                {data ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                        <div>
                            {paragrafos(data.resumo).map((p, i) => (
                                <p key={i} style={{ margin: "0 0 10px", fontSize: 15, lineHeight: 1.6, color: "var(--color-text)" }}>{p}</p>
                            ))}
                        </div>
                        {(data.temas ?? []).map((tema, i) => (
                            <div key={i}>
                                <h3 style={{ margin: "0 0 6px", fontSize: 16, color: "var(--color-heading)" }}>{tema.tema}</h3>
                                {tema.pontos?.length > 0 && (
                                    <ul style={{ margin: "0 0 8px", paddingLeft: 20, fontSize: 15, lineHeight: 1.55, color: "var(--color-text)" }}>
                                        {tema.pontos.map((p, j) => <li key={j}>{p}</li>)}
                                    </ul>
                                )}
                                {tema.citacoes?.map((c, j) => (
                                    <blockquote key={j} style={{ margin: "8px 0", padding: "8px 14px", borderLeft: "4px solid var(--color-primary-border)", backgroundColor: "var(--color-accent-soft)", borderRadius: "0 12px 12px 0", fontSize: 15, fontStyle: "italic", lineHeight: 1.5, color: "var(--color-text)" }}>
                                        “{c.texto}”
                                    </blockquote>
                                ))}
                            </div>
                        ))}
                        {data.lacunas?.length > 0 && (
                            <div>
                                <h3 style={{ margin: "0 0 6px", fontSize: 16, color: "var(--color-heading)" }}>O que ficou sem resposta</h3>
                                <ul style={{ margin: 0, paddingLeft: 20, fontSize: 15, lineHeight: 1.55, color: "var(--color-text)" }}>
                                    {data.lacunas.map((l, i) => <li key={i}>{l}</li>)}
                                </ul>
                            </div>
                        )}
                    </div>
                ) : concluida ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "flex-start" }}>
                        <p style={{ margin: 0, fontSize: 15, color: "var(--color-text-muted)" }}>A síntese desta entrevista ainda não foi gerada.</p>
                        <button className="ui-btn" style={{ ...ui.btnPrimario, opacity: gerando ? 0.6 : 1 }} onClick={gerar} disabled={gerando}>
                            <Sparkles size={17} aria-hidden="true" /> {gerando ? "Gerando… pode levar alguns segundos" : "Gerar síntese"}
                        </button>
                        {erroGerar && <p role="alert" style={{ margin: 0, color: "var(--color-error)", fontSize: 14 }}>{erroGerar}</p>}
                    </div>
                ) : (
                    <p style={{ margin: 0, fontSize: 15, color: "var(--color-text-muted)", display: "flex", gap: 8, alignItems: "center" }}>
                        <Info size={16} aria-hidden="true" /> Entrevista em andamento. A síntese pode ser gerada quando ela terminar.
                    </p>
                )}
            </EstadoTela>
        </section>
    );
}

export default function SessionDetailScreen() {
    const { sessionId } = useParams();
    const navigate = useNavigate();
    const detalhes = useApiResource(() => api.getSessionDetails(sessionId), [sessionId]);
    const [excluindo, setExcluindo] = useState(false);
    const [erroExcluir, setErroExcluir] = useState("");
    const [encerrando, setEncerrando] = useState(false);
    const [erroEncerrar, setErroEncerrar] = useState("");

    const d = detalhes.data;
    const sessao = d?.session;
    const roteiro = d?.script;
    const scriptId = sessao?.script_id;
    const pessoa = d?.participant?.apelido || "Anônimo";
    const voltarPara = scriptId ? `/entrevistas/${encodeURIComponent(scriptId)}` : "/entrevistas";

    async function encerrar() {
        if (!window.confirm("Encerrar esta entrevista? Depois não dá para continuar a conversa.")) return;
        setEncerrando(true);
        setErroEncerrar("");
        try {
            await api.finishSession(sessionId);
            await detalhes.recarregar();
        } catch (e) {
            setErroEncerrar(e.detail || "Não consegui encerrar a entrevista.");
        } finally {
            setEncerrando(false);
        }
    }

    async function excluir() {
        if (!window.confirm("Excluir esta entrevista? Isso apaga a conversa e a síntese, e não dá para desfazer.")) return;
        setExcluindo(true);
        setErroExcluir("");
        try {
            await api.deleteSession(sessionId);
            navigate(voltarPara);
        } catch (e) {
            setErroExcluir(e.detail || "Não consegui excluir a entrevista.");
            setExcluindo(false);
        }
    }

    return (
        <SideBar>
            <div style={ui.page}>
                <style>{CSS}</style>
                <button className="ui-btn" style={ui.voltar} onClick={() => navigate(voltarPara)}>
                    <ArrowLeft size={16} aria-hidden="true" /> {scriptId ? "Entrevistas do roteiro" : "Voltar"}
                </button>

                <EstadoTela carregando={detalhes.carregando} erro={detalhes.erro} onRetry={detalhes.recarregar}>
                    {sessao && (
                        <>
                            <div style={ui.topo}>
                                <div>
                                    <h1 style={ui.h1}>{roteiro?.titulo ?? "Entrevista"}</h1>
                                    <p style={ui.sub}>{pessoa} · {dataHora(sessao.created_at)}</p>
                                </div>
                                <StatusBadge status={sessao.status} />
                            </div>

                            {sessao.status === "em_andamento" && (
                                <p role="status" style={{ ...ui.card, margin: "0 0 16px", display: "flex", gap: 8, alignItems: "center", fontSize: 15, color: "var(--color-text)" }}>
                                    <Info size={16} aria-hidden="true" /> Entrevista em andamento.
                                    <button className="ui-btn" style={ui.btnSecundario} onClick={encerrar} disabled={encerrando}>
                                        {encerrando ? "Encerrando…" : "Encerrar entrevista"}
                                    </button>
                                </p>
                            )}
                            {erroEncerrar && (
                                <p role="alert" style={{ margin: "0 0 16px", color: "var(--color-error)", fontSize: 14 }}>{erroEncerrar}</p>
                            )}

                            <section style={ui.card} aria-labelledby="titulo-conversa">
                                <h2 id="titulo-conversa" style={H2}>Conversa</h2>
                                {sessao.conversation.length === 0 ? (
                                    <p style={{ margin: 0, color: "var(--color-text-muted)" }}>Ainda não há falas.</p>
                                ) : (
                                    <Transcricao turnos={sessao.conversation} perguntas={roteiro?.perguntas} pessoa={pessoa} />
                                )}
                            </section>

                            <Sintese key={sessionId} sessionId={sessionId} concluida={sessao.status === "concluida"} />

                            <div style={{ marginTop: 28, display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 6 }}>
                                <button className="ui-btn" style={ui.btnPerigo} onClick={excluir} disabled={excluindo}>
                                    <Trash2 size={16} aria-hidden="true" /> Excluir entrevista
                                </button>
                                {erroExcluir && <p role="alert" style={{ margin: 0, color: "var(--color-error)", fontSize: 14 }}>{erroExcluir}</p>}
                            </div>
                        </>
                    )}
                </EstadoTela>
            </div>
        </SideBar>
    );
}

const H2 = { margin: "0 0 14px", fontSize: 18, color: "var(--color-heading)", fontFamily: "var(--font-heading)" };
