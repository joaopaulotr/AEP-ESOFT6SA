
/**
 * Legenda ao vivo da fala da IA: mostra a frase que está tocando. `aria-live="polite"` para
 * leitor de tela acompanhar sem interromper; `aria-atomic` para ler a frase inteira.
 */
export default function LiveCaption({ texto, vazio = "Conectando à entrevista…" }) {
    return (
        <p style={s.texto} aria-live="polite" aria-atomic="true">
            {texto ? `"${texto}"` : vazio}
        </p>
    );
}

const s = {
    texto: { margin: 0, fontSize: 18, lineHeight: 1.5, color: "var(--color-text)", textAlign: "center", minHeight: 54 },
};
