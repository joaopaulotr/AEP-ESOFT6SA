import React, { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";

const MAX_LINHAS = 6;

/** Caixa de resposta do modo texto: Enter envia, Shift+Enter quebra a linha. */
export default function ChatComposer({ onSend, desabilitado = false, enviando = false }) {
    const [texto, setTexto] = useState("");
    const ref = useRef(null);
    const vazio = !texto.trim();
    const travado = desabilitado || enviando;

    useEffect(() => {
        const el = ref.current;
        if (!el) return;
        el.style.height = "auto";
        const linha = parseFloat(getComputedStyle(el).lineHeight) || 22;
        el.style.height = `${Math.min(el.scrollHeight, linha * MAX_LINHAS + 24)}px`;
    }, [texto]);

    // Devolve o foco ao campo quando ele volta a ficar utilizável (depois de enviar).
    const travadoAntes = useRef(travado);
    useEffect(() => {
        if (travadoAntes.current && !travado) ref.current?.focus();
        travadoAntes.current = travado;
    }, [travado]);

    async function enviar() {
        if (travado || vazio) return;
        const original = texto;
        setTexto("");
        const ok = await onSend(original.trim());
        if (ok === false) setTexto((atual) => atual || original); // falhou: devolve o rascunho
    }

    return (
        <div style={s.wrap}>
            <textarea
                ref={ref}
                rows={1}
                aria-label="Sua resposta"
                placeholder="Escreva sua resposta aqui…"
                style={s.textarea}
                value={texto}
                disabled={travado}
                onChange={(e) => setTexto(e.target.value)}
                onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                        e.preventDefault();
                        enviar();
                    }
                }}
            />
            <button
                className="ui-btn"
                style={{ ...s.btn, opacity: travado || vazio ? 0.5 : 1 }}
                disabled={travado || vazio}
                onClick={enviar}
                aria-label="Enviar resposta"
            >
                <Send size={18} aria-hidden="true" />
            </button>
        </div>
    );
}

const s = {
    wrap: { display: "flex", gap: 10, alignItems: "flex-end", padding: 12, borderTop: "1px solid var(--color-border)" },
    textarea: { flex: 1, minHeight: 48, resize: "none", overflowY: "auto", background: "var(--color-surface)", border: "1px solid var(--color-border-soft)", borderRadius: 15, padding: "12px 14px", color: "var(--color-text)", fontSize: 16, lineHeight: 1.45, fontFamily: "inherit", boxSizing: "border-box" },
    btn: { minHeight: "var(--touch-target)", minWidth: "var(--touch-target)", display: "inline-flex", alignItems: "center", justifyContent: "center", background: "var(--color-primary)", color: "var(--color-on-primary)", border: "none", borderRadius: 15, cursor: "pointer" },
};
