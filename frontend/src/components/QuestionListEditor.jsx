import { ArrowUp, ArrowDown, Trash2, Plus } from "lucide-react";
import { ui } from "../styles/ui";

export const MAX_PERGUNTAS = 20;

let contador = 0;
export function novoId() {
    if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
    contador += 1;
    return `q-${Date.now()}-${contador}`;
}

export function perguntaVazia() {
    return { id: novoId(), texto: "", objetivo: "", max_aprofundamentos: 2 };
}

export const campo = {
    width: "100%", boxSizing: "border-box", padding: "10px 12px", borderRadius: 12,
    border: "1px solid var(--color-border)", backgroundColor: "var(--color-input-bg)",
    color: "var(--color-text)", fontSize: 15, fontFamily: "var(--font-sans)",
};
export const rotulo = { display: "block", fontSize: 13.5, fontWeight: 600, color: "var(--color-text-2)", marginBottom: 4 };

/** Lista editável de perguntas: adicionar, remover, subir/descer. Cada item tem `id` estável (chave do React). */
export default function QuestionListEditor({ perguntas, onChange }) {
    function atualizar(id, parcial) {
        onChange(perguntas.map((p) => (p.id === id ? { ...p, ...parcial } : p)));
    }
    function mover(i, delta) {
        const j = i + delta;
        if (j < 0 || j >= perguntas.length) return;
        const copia = [...perguntas];
        [copia[i], copia[j]] = [copia[j], copia[i]];
        onChange(copia);
    }
    function remover(p, i) {
        if (p.texto.trim() && !window.confirm(`Remover a pergunta ${i + 1}?`)) return;
        onChange(perguntas.filter((x) => x.id !== p.id));
    }

    return (
        <div>
            <ol style={{ listStyle: "none", margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 14 }}>
                {perguntas.map((p, i) => (
                    <li key={p.id} style={{ ...ui.card, display: "flex", flexDirection: "column", gap: 10 }}>
                        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                            <strong style={{ color: "var(--color-heading)" }}>Pergunta {i + 1}</strong>
                            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                                <button type="button" className="ui-btn" style={ui.btnSecundario} disabled={i === 0}
                                    aria-label={`Mover pergunta ${i + 1} para cima`} onClick={() => mover(i, -1)}>
                                    <ArrowUp size={16} aria-hidden="true" /> Subir
                                </button>
                                <button type="button" className="ui-btn" style={ui.btnSecundario} disabled={i === perguntas.length - 1}
                                    aria-label={`Mover pergunta ${i + 1} para baixo`} onClick={() => mover(i, 1)}>
                                    <ArrowDown size={16} aria-hidden="true" /> Descer
                                </button>
                                <button type="button" className="ui-btn" style={ui.btnPerigo}
                                    aria-label={`Remover pergunta ${i + 1}`} onClick={() => remover(p, i)}>
                                    <Trash2 size={16} aria-hidden="true" />
                                </button>
                            </div>
                        </div>
                        <div>
                            <label style={rotulo} htmlFor={`texto-${p.id}`}>Texto da pergunta</label>
                            <textarea id={`texto-${p.id}`} style={{ ...campo, minHeight: 70 }} value={p.texto}
                                onChange={(e) => atualizar(p.id, { texto: e.target.value })} />
                        </div>
                        <div>
                            <label style={rotulo} htmlFor={`obj-${p.id}`}>Objetivo (opcional)</label>
                            <input id={`obj-${p.id}`} style={campo} value={p.objetivo}
                                onChange={(e) => atualizar(p.id, { objetivo: e.target.value })} />
                        </div>
                        <div>
                            <label style={rotulo} htmlFor={`apr-${p.id}`}>Máximo de aprofundamentos (0 a 5)</label>
                            <input id={`apr-${p.id}`} type="number" min={0} max={5} style={{ ...campo, maxWidth: 120 }}
                                value={p.max_aprofundamentos}
                                onChange={(e) => {
                                    const n = Number.parseInt(e.target.value, 10);
                                    atualizar(p.id, { max_aprofundamentos: Number.isNaN(n) ? 0 : Math.min(5, Math.max(0, n)) });
                                }} />
                        </div>
                    </li>
                ))}
            </ol>
            <div style={{ marginTop: 14 }}>
                <button type="button" className="ui-btn" style={ui.btnSecundario}
                    disabled={perguntas.length >= MAX_PERGUNTAS}
                    onClick={() => onChange([...perguntas, perguntaVazia()])}>
                    <Plus size={17} aria-hidden="true" /> Adicionar pergunta
                </button>
                {perguntas.length >= MAX_PERGUNTAS && (
                    <p style={ui.meta}>Limite de {MAX_PERGUNTAS} perguntas.</p>
                )}
            </div>
        </div>
    );
}
