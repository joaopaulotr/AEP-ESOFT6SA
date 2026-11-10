import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, UserPlus } from "lucide-react";
import SideBar from "../components/SideBar";
import EstadoTela from "../components/EstadoTela";
import StatTile from "../components/charts/StatTile";
import { BarChart, ColumnChart } from "../components/charts/BarChart";
import ScriptSynthesis from "../components/ScriptSynthesis";
import InviteModal from "../components/InviteModal";
import { useApiResource } from "../hooks/useApiResource";
import { api } from "../services/api";
import { ui, CSS } from "../styles/ui";

const INT = new Intl.NumberFormat("pt-BR");
const DEC = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const PCT = new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 0 });
const USD4 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 4, maximumFractionDigits: 4 });
const usd = (v) => `US$ ${USD4.format(v)}`;
const SEM_BASE = "Aparece quando houver entrevista concluída";

const ACOES = { deepen: "Aprofundou", advance: "Avançou", finish: "Encerrou" };
const CANAIS = { voz: "Voz", texto: "Texto", desconhecido: "Não informado" };

/** "2026-11-09" → "09/11" (sem passar por Date, para não deslocar o fuso). */
function diaMes(dia) {
    const [, m, d] = String(dia).split("-");
    return m && d ? `${d}/${m}` : String(dia);
}

export default function ScriptDashboardScreen() {
    const { scriptId } = useParams();
    const navigate = useNavigate();
    const { data: p, carregando, erro, recarregar } = useApiResource(() => api.getDashboard(scriptId), [scriptId]);
    const [convite, setConvite] = useState(null);
    const [abrindo, setAbrindo] = useState(false);
    const [erroConvite, setErroConvite] = useState("");

    async function convidar() {
        setAbrindo(true);
        setErroConvite("");
        try {
            const { link } = await api.getInvite(scriptId);
            setConvite({ script_id: scriptId, titulo: p.titulo, link_convite: link });
        } catch (e) {
            setErroConvite(e.detail || "Não consegui abrir o convite. Tente de novo.");
        } finally {
            setAbrindo(false);
        }
    }

    // null = sem base (nenhuma concluída / nenhum custo medido): mostra "—" em vez de um zero enganoso.
    const semConcluidas = !p || p.concluidas === 0;
    const duracao = semConcluidas ? null : p.duracao_media_min ?? null;
    const custo = semConcluidas ? null : p.custo_medio_usd ?? null;

    return (
        <SideBar>
            <div style={ui.page}>
                <style>{CSS}{GRID}</style>
                <button className="ui-btn" style={ui.voltar} onClick={() => navigate(`/entrevistas/${encodeURIComponent(scriptId)}`)}>
                    <ArrowLeft size={16} aria-hidden="true" /> Entrevistas do roteiro
                </button>
                <EstadoTela carregando={carregando} erro={erro} onRetry={recarregar} data={p}>
                    {p && (
                        <>
                            <div style={ui.topo}>
                                <div>
                                    <h1 style={ui.h1}>Painel: {p.titulo}</h1>
                                    <p style={ui.sub}>Números das entrevistas deste roteiro.</p>
                                </div>
                            </div>
                            {p.total_sessoes === 0 ? (
                                <div style={{ ...ui.card, ...ui.estado }}>
                                    <p style={{ ...ui.estadoTexto, fontWeight: 700, color: "var(--color-heading)" }}>Ainda não há entrevistas neste roteiro</p>
                                    <p style={ui.estadoTexto}>Convide participantes para ver os números aqui.</p>
                                    <button className="ui-btn" style={{ ...ui.btnPrimario, opacity: abrindo ? 0.6 : 1 }} onClick={convidar} disabled={abrindo}>
                                        <UserPlus size={17} aria-hidden="true" /> Convidar participantes
                                    </button>
                                    {erroConvite && <p role="alert" style={{ ...ui.estadoTexto, color: "var(--color-error)" }}>{erroConvite}</p>}
                                </div>
                            ) : (
                                <>
                                    <div className="painel-tiles">
                                        <StatTile rotulo="Entrevistas" valor={INT.format(p.total_sessoes)} detalhe={`${INT.format(p.concluidas)} concluídas · ${INT.format(p.em_andamento)} em andamento`} />
                                        <StatTile rotulo="Taxa de conclusão" valor={PCT.format(p.taxa_conclusao)} />
                                        <StatTile rotulo="Duração média" valor={duracao === null ? "—" : `${DEC.format(duracao)} min`}
                                            detalhe={duracao === null ? SEM_BASE : `${DEC.format(p.media_respostas)} respostas por entrevista`} />
                                        <StatTile rotulo="Custo médio" valor={custo === null ? "—" : usd(custo)}
                                            detalhe={custo === null ? SEM_BASE : `Média entre entrevistas com custo medido · total ${usd(p.custo_total_usd)} (estimativa)`} />
                                    </div>
                                    <div className="painel-graficos">
                                        <BarChart titulo="O que a entrevistadora fez" rotuloValor="Vezes" cor="var(--chart-1)"
                                            dados={p.acoes.map((a) => ({ rotulo: ACOES[a.acao] ?? a.acao, valor: a.total }))} />
                                        <BarChart titulo="Aprofundamentos por pergunta" rotuloValor="Média" cor="var(--chart-2)" formatar={(v) => DEC.format(v)}
                                            dados={p.aprofundamentos_por_pergunta.map((q) => ({ rotulo: `${q.pergunta_ordem}. ${q.texto}`, valor: q.media }))} />
                                        <BarChart titulo="Temas mais citados" rotuloValor="Entrevistas" cor="var(--chart-3)"
                                            dados={p.temas_mais_citados.map((t) => ({ rotulo: t.tema, valor: t.sessoes }))} />
                                        <BarChart titulo="Canais" rotuloValor="Entrevistas" cor="var(--chart-5)"
                                            dados={p.canais.map((c) => ({ rotulo: CANAIS[c.canal] ?? c.canal, valor: c.total }))} />
                                        <div style={{ gridColumn: "1 / -1" }}>
                                            <ColumnChart titulo="Entrevistas por dia" rotuloValor="Entrevistas" cor="var(--chart-1)"
                                                dados={p.sessoes_por_dia.map((d) => ({ rotulo: diaMes(d.dia), valor: d.total }))} />
                                        </div>
                                    </div>
                                </>
                            )}
                            {p.total_sessoes > 0 && <ScriptSynthesis scriptId={scriptId} sinteses={p.sinteses_sessao ?? p.concluidas} />}
                        </>
                    )}
                </EstadoTela>
                {convite && <InviteModal roteiro={convite} onClose={() => setConvite(null)} />}
            </div>
        </SideBar>
    );
}

const GRID = `.painel-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,200px),1fr));gap:12px;margin-bottom:16px}
.painel-graficos{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:16px}`;
