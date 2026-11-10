/**
 * Legenda da fala da IA: mostra a frase que está tocando. Não é região ao vivo: no modo voz o
 * anúncio para leitor de tela sai de uma única região (ver InterviewScreen), para não ler duas vezes.
 */
export default function LiveCaption({ texto, vazio = "Conectando à entrevista…" }) {
    return (
        <p style={s.texto}>
            {texto ? `"${texto}"` : vazio}
        </p>
    );
}

const s = {
    texto: { margin: 0, fontSize: 18, lineHeight: 1.5, color: "var(--color-text)", textAlign: "center", minHeight: 54 },
};
