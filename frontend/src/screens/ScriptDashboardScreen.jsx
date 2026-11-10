import React from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, UserPlus } from "lucide-react";
import SideBar from "../components/SideBar";
import EstadoTela from "../components/EstadoTela";
import StatTile from "../components/charts/StatTile";
import { BarChart, ColumnChart } from "../components/charts/BarChart";
import ScriptSynthesis from "../components/ScriptSynthesis";
import { useApiResource } from "../hooks/useApiResource";
import { api } from "../services/api";
import { ui, CSS } from "../styles/ui";

const INT = new Intl.NumberFormat("pt-BR");
const DEC = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const PCT = new Intl.NumberFormat("pt-BR", { style: "percent", maximumFractionDigits: 0 });
const USD4 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 4, maximumFractionDigits: 4 });
const usd = (v) => `US$ ${USD4.format(v)}`;

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
                                    <button className="ui-btn" style={ui.btnPrimario} onClick={() => navigate("/entrevistas")}>
                                        <UserPlus size={17} aria-hidden="true" /> Convidar participantes
                                    </button>
                                </div>
                            ) : (
                                <>
                                    <div className="painel-tiles">
                                        <StatTile rotulo="Entrevistas" valor={INT.format(p.total_sessoes)} detalhe={`${INT.format(p.concluidas)} concluídas · ${INT.format(p.em_andamento)} em andamento`} />
                                        <StatTile rotulo="Taxa de conclusão" valor={PCT.format(p.taxa_conclusao)} />
                                        <StatTile rotulo="Duração média" valor={`${DEC.format(p.duracao_media_min)} min`} detalhe={`${DEC.format(p.media_respostas)} respostas por entrevista`} />
                                        <StatTile rotulo="Custo médio" valor={usd(p.custo_medio_usd)} detalhe={`Total ${usd(p.custo_total_usd)} (estimativa)`} />
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
                            {p.total_sessoes > 0 && <ScriptSynthesis scriptId={scriptId} concluidas={p.concluidas} />}
                        </>
                    )}
                </EstadoTela>
            </div>
        </SideBar>
    );
}

const GRID = `.painel-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,200px),1fr));gap:12px;margin-bottom:16px}
.painel-graficos{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:16px}`;
