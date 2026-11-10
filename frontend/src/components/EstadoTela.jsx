import React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { ui } from "../styles/ui";

/** Carregando / erro (com "Tentar de novo") / vazio, para as telas de lista. */
export default function EstadoTela({ carregando, erro, onRetry, children }) {
    if (carregando) {
        return (
            <div style={ui.estado} role="status" aria-live="polite">
                <RefreshCw size={20} className="girando" aria-hidden="true" />
                <p style={ui.estadoTexto}>Carregando…</p>
            </div>
        );
    }
    if (erro) {
        return (
            <div style={ui.estado} role="alert">
                <AlertCircle size={20} aria-hidden="true" style={{ color: "var(--color-error)" }} />
                <p style={{ ...ui.estadoTexto, color: "var(--color-error)" }}>{erro}</p>
                {onRetry && <button className="ui-btn" style={ui.btnSecundario} onClick={onRetry}>Tentar de novo</button>}
            </div>
        );
    }
    return children;
}
