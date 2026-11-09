import React, { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Mic, FileText, MessageSquare } from "lucide-react";
import SideBar from "../components/SideBar";
import StatusBadge from "../components/StatusBadge";
import EstadoTela from "../components/EstadoTela";
import { useApiResource } from "../hooks/useApiResource";
import { api } from "../services/api";
import { dataHora } from "../utils/tempo";
import { ui, CSS } from "../styles/ui";

const FILTROS = [
    { valor: undefined, rotulo: "Todas" },
    { valor: "em_andamento", rotulo: "Em andamento" },
    { valor: "concluida", rotulo: "Concluídas" },
];

export default function ScriptSessionsScreen() {
    const { scriptId } = useParams();
    const navigate = useNavigate();
    const [status, setStatus] = useState(undefined);

    const roteiro = useApiResource(() => api.getScript(scriptId), [scriptId]);
    const sessoes = useApiResource(() => api.listScriptSessions(scriptId, { status }), [scriptId, status]);
    const lista = sessoes.data ?? [];

    function iniciar() {
        navigate(`/entrevista?roteiro=${encodeURIComponent(scriptId)}`);
    }

    return (
        <SideBar>
            <div style={ui.page}>
                <style>{CSS}{LISTA}</style>
                <button className="ui-btn" style={ui.voltar} onClick={() => navigate("/entrevistas")}>
                    <ArrowLeft size={16} aria-hidden="true" /> Todos os roteiros
                </button>

                <div style={ui.topo}>
                    <div>
                        <h1 style={ui.h1}>{roteiro.data?.titulo ?? "Entrevistas do roteiro"}</h1>
                        {roteiro.erro && <p style={{ ...ui.sub, color: "var(--color-error)" }} role="alert">{roteiro.erro}</p>}
                        {roteiro.data?.tema && <p style={ui.sub}>{roteiro.data.tema}</p>}
                        {roteiro.data && (
                            <p style={ui.sub}>
                                {roteiro.data.perguntas.length} perguntas · Entrevistadora: {roteiro.data.persona?.nome}
                            </p>
                        )}
                    </div>
                    <button className="ui-btn" style={ui.btnPrimario} onClick={iniciar}>
                        <Mic size={17} aria-hidden="true" /> Iniciar entrevista
                    </button>
                </div>

                <div role="group" aria-label="Filtrar por situação" style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
                    {FILTROS.map((f) => {
                        const ativo = f.valor === status;
                        return (
                            <button key={f.rotulo} className="ui-btn" aria-pressed={ativo}
                                onClick={() => setStatus(f.valor)}
                                style={{ ...(ativo ? ui.btnPrimario : ui.btnSecundario), boxShadow: "none" }}>
                                {f.rotulo}
                            </button>
                        );
                    })}
                </div>

                <EstadoTela carregando={sessoes.carregando} erro={sessoes.erro} onRetry={sessoes.recarregar}>
                    {lista.length === 0 ? (
                        <div style={ui.estado}>
                            <p style={{ ...ui.estadoTexto, fontWeight: 700, color: "var(--color-heading)" }}>Nenhuma entrevista ainda</p>
                            <button className="ui-btn" style={ui.btnPrimario} onClick={iniciar}>
                                <Mic size={17} aria-hidden="true" /> Iniciar entrevista
                            </button>
                        </div>
                    ) : (
                        <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 10 }}>
                            {lista.map((s) => (
                                <li key={s.session_id}>
                                    <button className="ui-card-link sessao-item" style={ui.card}
                                        onClick={() => navigate(`/sessao/${s.session_id}`)}>
                                        <span style={{ display: "flex", flexDirection: "column", gap: 4, textAlign: "left", minWidth: 0 }}>
                                            <strong style={{ color: "var(--color-heading)", fontSize: 15 }}>{s.participante || "Anônimo"}</strong>
                                            <span style={ui.meta}>{dataHora(s.created_at)}</span>
                                        </span>
                                        <span style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                                            <span style={{ ...ui.meta, display: "inline-flex", alignItems: "center", gap: 5 }}>
                                                <MessageSquare size={14} aria-hidden="true" /> {s.respostas} {s.respostas === 1 ? "resposta" : "respostas"}
                                            </span>
                                            {s.tem_sintese && (
                                                <span style={{ ...ui.meta, display: "inline-flex", alignItems: "center", gap: 5 }} title="Tem síntese">
                                                    <FileText size={14} aria-hidden="true" /> Síntese
                                                </span>
                                            )}
                                            <StatusBadge status={s.status} />
                                        </span>
                                    </button>
                                </li>
                            ))}
                        </ul>
                    )}
                </EstadoTela>
            </div>
        </SideBar>
    );
}

const LISTA = `.sessao-item{width:100%;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;cursor:pointer;font-family:var(--font-sans);text-align:left}
.sessao-item:hover{border-color:var(--color-primary-border)}`;
