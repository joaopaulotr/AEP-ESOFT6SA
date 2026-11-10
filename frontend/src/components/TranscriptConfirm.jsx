import { useEffect, useRef, useState } from "react";
import { Pencil, Send } from "lucide-react";

export const CONFIRMA_MS = 8000;

/**
 * Mostra o que foi entendido da fala e envia sozinho em 8 s; "Enviar agora" adianta, "Corrigir"
 * abre o texto para editar (só envia no botão "Enviar"). A contagem pausa enquanto o ponteiro ou o
 * foco estão no bloco. O bloco recebe o foco ao aparecer, para o leitor de tela ler o que foi entendido.
 */
export default function TranscriptConfirm({ texto, onEnviar, editarInicial = false }) {
    const [editando, setEditando] = useState(editarInicial);
    const [rascunho, setRascunho] = useState(texto);
    const [sobre, setSobre] = useState(false); // ponteiro em cima
    const [focado, setFocado] = useState(false);
    const onEnviarRef = useRef(onEnviar);
    onEnviarRef.current = onEnviar;
    const campoRef = useRef(null);
    const blocoRef = useRef(null);
    const restanteRef = useRef(CONFIRMA_MS);
    const pausado = sobre || focado;

    useEffect(() => {
        if (editando || pausado) return undefined;
        const inicio = Date.now();
        const t = setTimeout(() => onEnviarRef.current?.(texto), restanteRef.current);
        return () => {
            clearTimeout(t);
            restanteRef.current = Math.max(0, restanteRef.current - (Date.now() - inicio));
        };
    }, [editando, pausado, texto]);

    useEffect(() => {
        if (editando) campoRef.current?.focus();
    }, [editando]);

    useEffect(() => {
        if (!editarInicial) blocoRef.current?.focus({ preventScroll: true });
    }, [editarInicial]);

    if (editando) {
        return (
            <div style={s.caixa} role="group" aria-label="Corrigir o que foi entendido">
                <textarea
                    ref={campoRef}
                    aria-label="Corrija sua resposta"
                    style={s.campo}
                    rows={3}
                    value={rascunho}
                    onChange={(e) => setRascunho(e.target.value)}
                />
                <button
                    className="ui-btn"
                    style={s.btnEnviar}
                    disabled={!rascunho.trim()}
                    onClick={() => onEnviar?.(rascunho.trim())}
                >
                    <Send size={16} aria-hidden="true" /> Enviar
                </button>
            </div>
        );
    }

    // Foco no próprio bloco (tabIndex -1) não pausa: só pausa quando a pessoa entra num botão ou passa o ponteiro.
    return (
        <div
            ref={blocoRef}
            tabIndex={-1}
            style={s.caixa}
            role="group"
            aria-label="Confirmar o que foi entendido"
            aria-describedby="transcricao-entendida"
            onMouseEnter={() => setSobre(true)}
            onMouseLeave={() => setSobre(false)}
            onFocus={(e) => { if (e.target !== blocoRef.current) setFocado(true); }}
            onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget)) setFocado(false); }}
        >
            <p style={s.texto} id="transcricao-entendida">
                <span style={s.rotulo}>
                    {pausado ? "Entendi assim (envio automático pausado):" : "Entendi assim (envio automático em 8 s):"}
                </span>
                &ldquo;{texto}&rdquo;
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                <button className="ui-btn" style={s.btnEnviar} onClick={() => onEnviar?.(texto)}>
                    <Send size={16} aria-hidden="true" /> Enviar agora
                </button>
                <button className="ui-btn" style={s.btnCorrigir} onClick={() => { setRascunho(texto); setEditando(true); }}>
                    <Pencil size={16} aria-hidden="true" /> Corrigir
                </button>
            </div>
        </div>
    );
}

const botao = {
    minHeight: "var(--touch-target)",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderRadius: 15,
    padding: "0 16px",
    fontSize: 15,
    fontWeight: 600,
    cursor: "pointer",
};

const s = {
    caixa: { outline: "none", width: "100%", boxSizing: "border-box", display: "flex", flexDirection: "column", gap: 10, background: "var(--color-surface-2)", border: "1px solid var(--color-border)", borderRadius: 15, padding: 14 },
    texto: { margin: 0, fontSize: 15, lineHeight: 1.45, color: "var(--color-text)" },
    rotulo: { display: "block", fontSize: 12.5, fontWeight: 700, color: "var(--color-text-muted)", marginBottom: 2 },
    campo: { width: "100%", boxSizing: "border-box", resize: "vertical", background: "var(--color-surface)", border: "1px solid var(--color-border-soft)", borderRadius: 12, padding: "10px 12px", color: "var(--color-text)", fontSize: 16, lineHeight: 1.45, fontFamily: "inherit" },
    btnCorrigir: { ...botao, background: "var(--color-surface)", color: "var(--color-text)", border: "1px solid var(--color-border)" },
    btnEnviar: { ...botao, alignSelf: "flex-end", background: "var(--color-primary)", color: "var(--color-on-primary)", border: "none" },
};
