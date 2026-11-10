import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Mic, PenLine } from "lucide-react";
import PublicLayout from "../components/PublicLayout";
import EstadoTela from "../components/EstadoTela";
import { api, ApiError } from "../services/api";
import { ui } from "../styles/ui";
import { estimativaMinutos } from "../utils/tempo";
import { guardarSessaoPublica } from "../utils/sessaoPublica";

const FAIXAS = ["até 17", "18–29", "30–44", "45–59", "60+"];

export default function InviteScreen() {
    const { slug } = useParams();
    const navigate = useNavigate();
    const [convite, setConvite] = useState(null);
    const [carregando, setCarregando] = useState(true);
    const [erro, setErro] = useState("");
    const [naoExiste, setNaoExiste] = useState(false);

    const carregar = useCallback(async () => {
        setCarregando(true);
        setErro("");
        setNaoExiste(false);
        try {
            setConvite(await api.getPublicInvite(slug));
        } catch (e) {
            if (e instanceof ApiError && e.status === 404) setNaoExiste(true);
            else setErro(e?.detail || "Não consegui abrir o convite. Tente de novo.");
        } finally {
            setCarregando(false);
        }
    }, [slug]);

    useEffect(() => { carregar(); }, [carregar]);
    const [canal, setCanal] = useState("voz");
    const [apelido, setApelido] = useState("");
    const [faixa, setFaixa] = useState("");
    const [regiao, setRegiao] = useState("");
    const [enviando, setEnviando] = useState(false);
    const [erroInicio, setErroInicio] = useState("");
    const travaRef = useRef(false);

    async function comecar() {
        if (travaRef.current) return;
        travaRef.current = true;
        setEnviando(true);
        setErroInicio("");
        try {
            const dados = await api.startFromInvite(slug, {
                canal,
                apelido: apelido.trim() || undefined,
                faixa_etaria: faixa || undefined,
                regiao: regiao.trim() || undefined,
            });
            // O id da sessão fica no sessionStorage (por slug), nunca na URL.
            guardarSessaoPublica(slug, { sessionId: dados.session_id, canal: canal === "texto" ? "texto" : "voz" });
            navigate(`/e/${encodeURIComponent(slug)}/entrevista`);
        } catch (e) {
            setErroInicio(e?.detail || "Não consegui começar agora. Tente de novo em instantes.");
            travaRef.current = false;
            setEnviando(false);
        }
    }

    const nome = convite?.persona?.nome || "Ana";

    return (
        <PublicLayout>
            <div style={{ ...ui.page, maxWidth: 640 }}>
                {naoExiste && (
                    <p role="alert" style={{ ...ui.card, textAlign: "center", fontSize: 16 }}>
                        Esse convite não existe ou foi encerrado.
                    </p>
                )}
                <EstadoTela carregando={carregando && !naoExiste} erro={erro} onRetry={carregar} data={convite}>
                    {convite && (
                        <div style={ui.card}>
                            <h1 style={ui.h1}>Oi, eu sou a {nome}.</h1>
                            <p style={{ ...ui.sub, fontSize: 16 }}>
                                Vou conversar com você sobre <strong>{convite.titulo}</strong>.
                            </p>
                            {convite.tema && <p style={ui.sub}>Tema: {convite.tema}</p>}
                            {convite.descricao && <p style={ui.sub}>{convite.descricao}</p>}
                            <p style={{ ...ui.sub, color: "var(--color-text)" }}>
                                Leva uns {estimativaMinutos(convite.perguntas_total)} minutos. Não há resposta certa ou errada: só conte o que você pensa.
                            </p>

                            <h2 style={s.h2} id="como-responder">Como você prefere responder?</h2>
                            <div style={s.escolha} role="group" aria-labelledby="como-responder">
                                <button type="button" className="ui-btn" aria-pressed={canal === "voz"} onClick={() => setCanal("voz")} style={{ ...s.opcao, ...(canal === "voz" ? s.opcaoAtiva : {}) }}>
                                    <Mic size={26} aria-hidden="true" /> Falar
                                </button>
                                <button type="button" className="ui-btn" aria-pressed={canal === "texto"} onClick={() => setCanal("texto")} style={{ ...s.opcao, ...(canal === "texto" ? s.opcaoAtiva : {}) }}>
                                    <PenLine size={26} aria-hidden="true" /> Escrever
                                </button>
                            </div>

                            <h2 style={s.h2}>Se quiser, conte um pouco sobre você</h2>
                            <p style={{ ...ui.meta, margin: "0 0 10px" }}>É opcional: pode deixar em branco.</p>
                            <label style={s.label}>
                                Como prefere ser chamado(a)?
                                <input style={s.input} value={apelido} maxLength={40} onChange={(e) => setApelido(e.target.value)} autoComplete="off" />
                            </label>
                            <label style={s.label}>
                                Faixa etária
                                <select style={s.input} value={faixa} onChange={(e) => setFaixa(e.target.value)}>
                                    <option value="">Prefiro não dizer</option>
                                    {FAIXAS.map((f) => <option key={f} value={f}>{f}</option>)}
                                </select>
                            </label>
                            <label style={s.label}>
                                Cidade ou bairro
                                <input style={s.input} value={regiao} maxLength={60} onChange={(e) => setRegiao(e.target.value)} autoComplete="off" />
                            </label>

                            {erroInicio && <p role="alert" style={{ color: "var(--color-error)", margin: "8px 0" }}>{erroInicio}</p>}
                            <button type="button" className="ui-btn" style={{ ...ui.btnPrimario, width: "100%", fontSize: 17, opacity: enviando ? 0.6 : 1 }} disabled={enviando} onClick={comecar}>
                                {enviando ? "Começando…" : "Começar"}
                            </button>
                        </div>
                    )}
                </EstadoTela>
            </div>
        </PublicLayout>
    );
}

const s = {
    h2: { margin: "22px 0 8px", fontSize: 17, color: "var(--color-heading)" },
    escolha: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 },
    opcao: { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8, minHeight: 96, borderRadius: 18, border: "2px solid var(--color-border)", background: "var(--color-surface)", color: "var(--color-text)", fontSize: 17, fontWeight: 700, cursor: "pointer", fontFamily: "var(--font-sans)" },
    opcaoAtiva: { borderColor: "var(--color-primary)", background: "var(--color-accent-soft)", color: "var(--color-primary)" },
    label: { display: "flex", flexDirection: "column", gap: 6, marginBottom: 12, fontSize: 14.5, fontWeight: 600, color: "var(--color-text)" },
    input: { minHeight: "var(--touch-target)", padding: "0 12px", borderRadius: 12, border: "1px solid var(--color-border-soft)", background: "var(--color-input-bg)", color: "var(--color-text)", fontSize: 16, fontFamily: "inherit", boxSizing: "border-box", width: "100%" },
};
