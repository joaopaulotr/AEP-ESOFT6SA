import { useEffect, useRef } from "react";
import { HeartHandshake } from "lucide-react";
import { ui } from "../styles/ui";

export const TEXTO_CVV = "Se precisar, fale com o CVV: ligue 188 (grátis, 24 h) ou acesse cvv.org.br";

/**
 * Cartão fixo do CVV, mostrado quando a entrevista terminou em acolhimento. Não some sozinho.
 * `focar`: recebe o foco ao aparecer (leitor de tela lê o cartão inteiro).
 * `aoContinuar` + `podeContinuar`: botão "Continuar" (na entrevista, só depois da fala final).
 */
export default function CvvAviso({ focar = false, aoContinuar, podeContinuar = true }) {
    const ref = useRef(null);
    useEffect(() => {
        if (focar) ref.current?.focus();
    }, [focar]);

    return (
        <section ref={ref} tabIndex={-1} aria-labelledby="cvv-titulo" style={s.caixa}>
            <h2 id="cvv-titulo" style={s.titulo}>
                <HeartHandshake size={20} aria-hidden="true" /> Você não está sozinho(a)
            </h2>
            <p style={s.texto}>
                Se precisar, fale com o CVV: ligue <a href="tel:188" style={s.link}>188</a> (grátis, 24 h) ou acesse{" "}
                <a href="https://cvv.org.br" target="_blank" rel="noopener noreferrer" style={s.link}>cvv.org.br</a>
            </p>
            {aoContinuar && (
                <button type="button" className="ui-btn" style={{ ...ui.btnPrimario, alignSelf: "flex-start", opacity: podeContinuar ? 1 : 0.6 }}
                    disabled={!podeContinuar} onClick={aoContinuar}>
                    Continuar
                </button>
            )}
        </section>
    );
}

const s = {
    caixa: { display: "flex", flexDirection: "column", gap: 10, padding: 18, marginBottom: 16, borderRadius: 18, border: "2px solid var(--color-primary-border)", backgroundColor: "var(--color-accent-soft)", boxSizing: "border-box", outline: "none" },
    titulo: { margin: 0, display: "flex", alignItems: "center", gap: 8, fontSize: 18, color: "var(--color-heading)", fontFamily: "var(--font-heading)" },
    texto: { margin: 0, fontSize: 16, lineHeight: 1.5, color: "var(--color-text)" },
    link: { color: "var(--color-primary)", fontWeight: 700 },
};
