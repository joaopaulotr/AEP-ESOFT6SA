import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Mic, List, User, Plus, Upload, Pencil, UserPlus } from "lucide-react";
import SideBar from "../components/SideBar";
import InviteModal from "../components/InviteModal";
import EstadoTela from "../components/EstadoTela";
import { useApiResource } from "../hooks/useApiResource";
import { api } from "../services/api";
import { ui, CSS } from "../styles/ui";
import { limparRascunho } from "./ScriptEditorScreen";

export default function ScriptsScreen() {
    const navigate = useNavigate();
    const { data, carregando, erro, recarregar } = useApiResource(() => api.listScripts(), []);
    const roteiros = data ?? [];
    const [convite, setConvite] = useState(null);

    return (
        <SideBar>
            <div style={ui.page}>
                <style>{CSS}{GRID}</style>
                <div style={ui.topo}>
                    <div>
                        <h1 style={ui.h1}>Entrevistas</h1>
                        <p style={ui.sub}>Escolha um roteiro para começar uma entrevista ou ver as que já foram feitas.</p>
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                        <button className="ui-btn" style={ui.btnPrimario}
                            onClick={() => { limparRascunho(); navigate("/roteiros/novo"); }}>
                            <Plus size={17} aria-hidden="true" /> Novo roteiro
                        </button>
                        <button className="ui-btn" style={ui.btnSecundario} onClick={() => navigate("/roteiros/importar")}>
                            <Upload size={17} aria-hidden="true" /> Subir questionário
                        </button>
                    </div>
                </div>

                <EstadoTela carregando={carregando} erro={erro} onRetry={recarregar} data={data}>
                    {roteiros.length === 0 ? (
                        <div style={ui.estado}><p style={ui.estadoTexto}>Nenhum roteiro disponível ainda.</p></div>
                    ) : (
                        <div className="roteiros-grid">
                            {roteiros.map((r) => (
                                <article key={r.script_id} style={{ ...ui.card, display: "flex", flexDirection: "column", gap: 10 }}>
                                    <h2 style={{ margin: 0, fontSize: 18, color: "var(--color-heading)", fontFamily: "var(--font-heading)" }}>{r.titulo}</h2>
                                    {r.tema && <p style={{ margin: 0, fontSize: 14, color: "var(--color-text-2)" }}>{r.tema}</p>}
                                    <p style={{ ...ui.meta, margin: 0 }}>
                                        {r.perguntas_total} {r.perguntas_total === 1 ? "pergunta" : "perguntas"}
                                    </p>
                                    <p style={{ ...ui.meta, margin: 0 }}>
                                        {r.concluidas} {r.concluidas === 1 ? "concluída" : "concluídas"} · {r.em_andamento} em andamento
                                    </p>
                                    <p style={{ ...ui.meta, margin: 0, display: "flex", alignItems: "center", gap: 6 }}>
                                        <User size={14} aria-hidden="true" /> Entrevistadora: {r.persona?.nome}
                                    </p>
                                    <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: "auto", paddingTop: 8 }}>
                                        <button className="ui-btn" style={ui.btnPrimario}
                                            onClick={() => navigate(`/entrevista?roteiro=${encodeURIComponent(r.script_id)}`)}>
                                            <Mic size={17} aria-hidden="true" /> Iniciar entrevista
                                        </button>
                                        <button className="ui-btn" style={ui.btnSecundario}
                                            onClick={() => navigate(`/entrevistas/${encodeURIComponent(r.script_id)}`)}>
                                            <List size={17} aria-hidden="true" /> Ver entrevistas
                                        </button>
                                        <button className="ui-btn" style={ui.btnSecundario}
                                            aria-label={`Convidar para ${r.titulo}`}
                                            onClick={() => setConvite(r)}>
                                            <UserPlus size={17} aria-hidden="true" /> Convidar
                                        </button>
                                        <button className="ui-btn" style={ui.btnSecundario}
                                            aria-label={`Editar roteiro ${r.titulo}`}
                                            onClick={() => navigate(`/roteiros/${encodeURIComponent(r.script_id)}/editar`)}>
                                            <Pencil size={17} aria-hidden="true" /> Editar
                                        </button>
                                    </div>
                                </article>
                            ))}
                        </div>
                    )}
                </EstadoTela>
                {convite && <InviteModal roteiro={convite} onClose={() => setConvite(null)} />}
            </div>
        </SideBar>
    );
}

const GRID = `.roteiros-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,300px),1fr));gap:16px}`;
