import React, { useEffect, useRef, useState } from "react";
import { Pencil, Send } from "lucide-react";

export const CONFIRMA_MS = 3000;

/**
 * Mostra o que foi entendido da fala por 3 s e envia sozinho; "Corrigir" abre o texto para editar
 * e só envia no botão "Enviar". O envio automático para quando a pessoa começa a corrigir.
 */
export default function TranscriptConfirm({ texto, onEnviar }) {
    const [editando, setEditando] = useState(false);
    const [rascunho, setRascunho] = useState(texto);
    const onEnviarRef = useRef(onEnviar);
    onEnviarRef.current = onEnviar;
    const campoRef = useRef(null);

    useEffect(() => {
        if (editando) return undefined;
        const t = setTimeout(() => onEnviarRef.current?.(texto), CONFIRMA_MS);
        return () => clearTimeout(t);
    }, [editando, texto]);

    useEffect(() => {
        if (editando) campoRef.current?.focus();
    }, [editando]);

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

    return (
        <div style={s.caixa} role="group" aria-label="Confirmar o que foi entendido">
            <p style={s.texto} aria-live="polite">
                <span style={s.rotulo}>Entendi assim (envio em 3 s):</span> "{texto}"
            </p>
            <button className="ui-btn" style={s.btnCorrigir} onClick={() => { setRascunho(texto); setEditando(true); }}>
                <Pencil size={16} aria-hidden="true" /> Corrigir
            </button>
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
    caixa: { width: "100%", boxSizing: "border-box", display: "flex", flexDirection: "column", gap: 10, background: "var(--color-surface-2)", border: "1px solid var(--color-border)", borderRadius: 15, padding: 14 },
    texto: { margin: 0, fontSize: 15, lineHeight: 1.45, color: "var(--color-text)" },
    rotulo: { display: "block", fontSize: 12.5, fontWeight: 700, color: "var(--color-text-muted)", marginBottom: 2 },
    campo: { width: "100%", boxSizing: "border-box", resize: "vertical", background: "var(--color-surface)", border: "1px solid var(--color-border-soft)", borderRadius: 12, padding: "10px 12px", color: "var(--color-text)", fontSize: 16, lineHeight: 1.45, fontFamily: "inherit" },
    btnCorrigir: { ...botao, alignSelf: "flex-start", background: "var(--color-surface)", color: "var(--color-text)", border: "1px solid var(--color-border)" },
    btnEnviar: { ...botao, alignSelf: "flex-end", background: "var(--color-primary)", color: "var(--color-on-primary)", border: "none" },
};
