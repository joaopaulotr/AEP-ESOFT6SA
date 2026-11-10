import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, AlertTriangle, Info, Lock, Unlock } from "lucide-react";
import SideBar from "../components/SideBar";
import EstadoTela from "../components/EstadoTela";
import QuestionListEditor, { campo, rotulo, novoId, perguntaVazia } from "../components/QuestionListEditor";
import { useApiResource } from "../hooks/useApiResource";
import { ApiError, api } from "../services/api";
import { ui, CSS } from "../styles/ui";

const CHAVE_RASCUNHO = "roteiro-rascunho";

export function guardarRascunho(rascunho) {
    try { sessionStorage.setItem(CHAVE_RASCUNHO, JSON.stringify(rascunho)); } catch { /* sem storage: segue só com o state */ }
}

export function limparRascunho() {
    try { sessionStorage.removeItem(CHAVE_RASCUNHO); } catch { /* ignorado */ }
}

function lerRascunho() {
    try {
        const bruto = sessionStorage.getItem(CHAVE_RASCUNHO);
        return bruto ? JSON.parse(bruto) : null;
    } catch {
        return null;
    }
}

function paraPerguntas(lista) {
    return (lista ?? []).map((p) => ({
        id: novoId(),
        texto: p.texto ?? "",
        objetivo: p.objetivo ?? "",
        max_aprofundamentos: p.max_aprofundamentos ?? 2,
    }));
}

function formVazio() {
    return { titulo: "", tema: "", descricao: "", persona: { nome: "Ana", tom: "acolhedor" }, perguntas: [perguntaVazia()] };
}

function formDe(fonte) {
    return {
        titulo: fonte.titulo ?? "",
        tema: fonte.tema ?? "",
        descricao: fonte.descricao ?? "",
        persona: fonte.persona ?? { nome: "Ana", tom: "acolhedor" },
        perguntas: fonte.perguntas?.length ? paraPerguntas(fonte.perguntas) : [perguntaVazia()],
    };
}

function perguntasParaApi(perguntas) {
    return perguntas
        .filter((p) => p.texto.trim())
        .map((p) => ({ texto: p.texto.trim(), objetivo: p.objetivo.trim(), max_aprofundamentos: p.max_aprofundamentos }));
}

function mesmasPerguntas(a, b) {
    return JSON.stringify(a) === JSON.stringify(b);
}

const CONFIRMA_DESCARTE = "Sair sem salvar? As alterações feitas aqui serão perdidas.";

/** Formulário em forma comparável (ignora os ids internos das perguntas). */
function assinatura(form) {
    return JSON.stringify({ ...form, perguntas: form.perguntas.map(({ id: _id, ...p }) => p) });
}

export default function ScriptEditorScreen() {
    const { scriptId } = useParams();
    const edicao = Boolean(scriptId);
    const { data: carregado, carregando, erro: erroCarga, recarregar } = useApiResource(
        () => (edicao ? api.getScript(scriptId) : Promise.resolve(null)),
        [scriptId],
    );

    // O formulário registra aqui o seu "sair" (que pede confirmação se houver alterações).
    const sairRef = useRef(null);

    if (edicao) {
        return (
            <Moldura titulo="Editar roteiro" sairRef={sairRef}>
                <EstadoTela carregando={carregando} erro={erroCarga} onRetry={recarregar} data={carregado}>
                    {carregado && <Formulario key={carregado.script_id} script={carregado} sairRef={sairRef} />}
                </EstadoTela>
            </Moldura>
        );
    }
    return (
        <Moldura titulo="Novo roteiro" sairRef={sairRef}>
            <Formulario sairRef={sairRef} />
        </Moldura>
    );
}

function Moldura({ titulo, sairRef, children }) {
    const navigate = useNavigate();
    return (
        <SideBar>
            <div style={ui.page}>
                <style>{CSS}</style>
                <button className="ui-btn" style={ui.voltar} onClick={() => (sairRef.current ? sairRef.current() : navigate("/entrevistas"))}>
                    <ArrowLeft size={16} aria-hidden="true" /> Voltar
                </button>
                <h1 style={{ ...ui.h1, marginBottom: 18 }}>{titulo}</h1>
                {children}
            </div>
        </SideBar>
    );
}

/** Abre/encerra o convite do roteiro (`ativo`). Encerrado: o link e o QR param de abrir a entrevista. */
function ControleConvite({ script }) {
    const [ativo, setAtivo] = useState(script.ativo !== false);
    const [mudando, setMudando] = useState(false);
    const [mensagem, setMensagem] = useState("");

    async function alternar() {
        if (ativo && !window.confirm("Encerrar o convite? O link e o QR Code deixam de abrir a entrevista.")) return;
        setMudando(true);
        setMensagem("");
        try {
            await api.updateScript(script.script_id, { ativo: !ativo });
            setAtivo(!ativo);
            setMensagem(ativo
                ? "Convite encerrado. O roteiro sai da lista de entrevistas até ser reaberto aqui."
                : "Convite reaberto. O link e o QR Code voltaram a funcionar.");
        } catch (err) {
            setMensagem(err instanceof ApiError && err.detail ? err.detail : "Não consegui mudar o convite. Tente de novo.");
        } finally {
            setMudando(false);
        }
    }

    return (
        <section style={{ ...ui.card, display: "flex", flexDirection: "column", gap: 10 }} aria-labelledby="convite-estado">
            <h2 id="convite-estado" style={{ margin: 0, fontSize: 17, color: "var(--color-heading)", fontFamily: "var(--font-heading)" }}>
                Convite {ativo ? "aberto" : "encerrado"}
            </h2>
            <p style={{ margin: 0, fontSize: 14.5, color: "var(--color-text-2)" }}>
                {ativo ? "Quem tiver o link ou o QR Code pode responder." : "O link e o QR Code não abrem a entrevista."}
            </p>
            <div>
                <button type="button" className="ui-btn" style={{ ...(ativo ? ui.btnSecundario : ui.btnPrimario), opacity: mudando ? 0.6 : 1 }}
                    disabled={mudando} onClick={alternar}>
                    {ativo ? <Lock size={16} aria-hidden="true" /> : <Unlock size={16} aria-hidden="true" />}
                    {ativo ? "Encerrar convite" : "Reabrir convite"}
                </button>
            </div>
            <p role="status" style={{ margin: 0, minHeight: 18, fontSize: 14, color: "var(--color-text)" }}>{mensagem}</p>
        </section>
    );
}

function Formulario({ script, sairRef }) {
    const navigate = useNavigate();
    const location = useLocation();
    const [rascunho] = useState(() => (script ? null : location.state?.rascunho ?? lerRascunho()));
    const [form, setForm] = useState(() => (script ? formDe(script) : rascunho ? formDe(rascunho) : formVazio()));
    const [salvando, setSalvando] = useState(false);
    const [erro, setErro] = useState("");
    const [inicial] = useState(() => assinatura(form));
    const alterado = !salvando && assinatura(form) !== inicial;

    // O rascunho importado vale enquanto esta tela está aberta (sobrevive ao recarregar); ao sair
    // dela, some: "Novo roteiro" depois não traz de volta um questionário antigo.
    useEffect(() => {
        if (script) return undefined;
        if (rascunho) guardarRascunho(rascunho);
        else limparRascunho();
        return () => limparRascunho();
    }, [rascunho, script]);

    // Fechar/recarregar a aba com alterações: o navegador pede confirmação.
    useEffect(() => {
        if (!alterado) return undefined;
        const aviso = (e) => {
            e.preventDefault();
            e.returnValue = "";
        };
        window.addEventListener("beforeunload", aviso);
        return () => window.removeEventListener("beforeunload", aviso);
    }, [alterado]);

    function sair() {
        if (alterado && !window.confirm(CONFIRMA_DESCARTE)) return;
        navigate("/entrevistas");
    }
    useEffect(() => {
        sairRef.current = sair;
        return () => { sairRef.current = null; };
    });

    const avisos = rascunho?.avisos ?? [];
    const set = (parcial) => setForm((f) => ({ ...f, ...parcial }));

    function validar() {
        if (!form.titulo.trim()) return "Dê um título ao roteiro.";
        if (perguntasParaApi(form.perguntas).length === 0) return "Escreva pelo menos uma pergunta.";
        return "";
    }

    async function salvar(e) {
        e.preventDefault();
        const problema = validar();
        if (problema) { setErro(problema); return; }
        setErro("");
        setSalvando(true);
        try {
            const perguntas = perguntasParaApi(form.perguntas);
            const persona = { nome: form.persona.nome.trim() || "Ana", tom: form.persona.tom };
            if (script) {
                const dados = {};
                if (form.titulo.trim() !== script.titulo) dados.titulo = form.titulo.trim();
                if (form.tema.trim() !== (script.tema ?? "")) dados.tema = form.tema.trim();
                if (form.descricao.trim() !== (script.descricao ?? "")) dados.descricao = form.descricao.trim();
                if (persona.nome !== script.persona?.nome || persona.tom !== script.persona?.tom) dados.persona = persona;
                const originais = script.perguntas.map((p) => ({
                    texto: (p.texto ?? "").trim(), objetivo: (p.objetivo ?? "").trim(), max_aprofundamentos: p.max_aprofundamentos,
                }));
                if (!mesmasPerguntas(perguntas, originais)) dados.perguntas = perguntas;
                if (Object.keys(dados).length > 0) await api.updateScript(script.script_id, dados);
            } else {
                const dados = {
                    titulo: form.titulo.trim(), tema: form.tema.trim(), descricao: form.descricao.trim(),
                    perguntas, persona,
                };
                if (rascunho?.origem) dados.origem = rascunho.origem;
                await api.createScript(dados);
                limparRascunho();
            }
            navigate("/entrevistas", { replace: true });
        } catch (err) {
            setErro(err instanceof ApiError && err.detail ? err.detail : "Não consegui salvar. Tente de novo.");
            setSalvando(false);
        }
    }

    return (
        <form onSubmit={salvar} noValidate style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            {rascunho && (
                <div style={{ ...ui.card, borderColor: "var(--color-primary-border)", display: "flex", flexDirection: "column", gap: 8 }}>
                    <p style={{ margin: 0, display: "flex", gap: 8, alignItems: "center", fontWeight: 600, color: "var(--color-heading)" }}>
                        <Info size={18} aria-hidden="true" /> Revise as perguntas antes de publicar.
                    </p>
                    {avisos.length > 0 && (
                        <ul style={{ margin: 0, paddingLeft: 20, color: "var(--color-text-2)", fontSize: 14.5 }}>
                            {avisos.map((a, i) => (
                                <li key={i}><AlertTriangle size={14} aria-hidden="true" style={{ verticalAlign: "-2px", marginRight: 4 }} />{a}</li>
                            ))}
                        </ul>
                    )}
                </div>
            )}

            <section style={{ ...ui.card, display: "flex", flexDirection: "column", gap: 12 }} aria-label="Dados do roteiro">
                <div>
                    <label style={rotulo} htmlFor="titulo">Título</label>
                    <input id="titulo" style={campo} value={form.titulo} required aria-required="true"
                        onChange={(e) => set({ titulo: e.target.value })} />
                </div>
                <div>
                    <label style={rotulo} htmlFor="tema">Tema (opcional)</label>
                    <input id="tema" style={campo} value={form.tema} onChange={(e) => set({ tema: e.target.value })} />
                </div>
                <div>
                    <label style={rotulo} htmlFor="descricao">Descrição (opcional)</label>
                    <textarea id="descricao" style={{ ...campo, minHeight: 70 }} value={form.descricao}
                        onChange={(e) => set({ descricao: e.target.value })} />
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
                    <div style={{ flex: "1 1 180px" }}>
                        <label style={rotulo} htmlFor="persona-nome">Nome da entrevistadora</label>
                        <input id="persona-nome" style={campo} value={form.persona.nome}
                            onChange={(e) => set({ persona: { ...form.persona, nome: e.target.value } })} />
                    </div>
                    <div style={{ flex: "1 1 180px" }}>
                        <label style={rotulo} htmlFor="persona-tom">Tom da conversa</label>
                        <select id="persona-tom" style={campo} value={form.persona.tom}
                            onChange={(e) => set({ persona: { ...form.persona, tom: e.target.value } })}>
                            <option value="acolhedor">Acolhedor</option>
                            <option value="neutro">Neutro</option>
                            <option value="formal">Formal</option>
                        </select>
                    </div>
                </div>
            </section>

            <section aria-label="Perguntas">
                <h2 style={{ margin: "0 0 10px", fontSize: 18, color: "var(--color-heading)", fontFamily: "var(--font-heading)" }}>Perguntas</h2>
                <QuestionListEditor perguntas={form.perguntas} onChange={(perguntas) => set({ perguntas })} />
            </section>

            {erro && <p role="alert" style={{ margin: 0, color: "var(--color-error)", fontSize: 15 }}>{erro}</p>}

            <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                <button type="submit" className="ui-btn" style={ui.btnPrimario} disabled={salvando}>
                    {salvando ? "Salvando…" : script ? "Salvar" : "Publicar"}
                </button>
                <button type="button" className="ui-btn" style={ui.btnSecundario} onClick={sair}>
                    Cancelar
                </button>
                {alterado && <span style={{ ...ui.meta, alignSelf: "center" }}>Alterações não salvas</span>}
            </div>
            {script && <ControleConvite script={script} />}
        </form>
    );
}
