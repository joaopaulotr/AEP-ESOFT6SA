import { AlertCircle, RefreshCw } from "lucide-react";
import { ui } from "../styles/ui";

/**
 * Carregando / erro (com "Tentar de novo") / conteúdo, para as telas de lista.
 * `data`: dado já carregado. Primeira carga (sem dado) mostra a tela cheia de
 * "Carregando…"; recarregar com dado na tela mostra o conteúdo + "Atualizando…" discreto.
 */
export default function EstadoTela({ carregando, erro, onRetry, data, children }) {
    if (carregando && !data) {
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
    return (
        <>
            {carregando && (
                <p role="status" aria-live="polite" style={{ ...ui.meta, margin: "0 0 12px" }}>Atualizando…</p>
            )}
            {children}
        </>
    );
}
