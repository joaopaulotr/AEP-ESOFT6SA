import { Heart } from "lucide-react";
import PublicLayout from "../components/PublicLayout";
import { ui } from "../styles/ui";

export default function ThankYouScreen() {
    return (
        <PublicLayout>
            <div style={{ ...ui.page, maxWidth: 560 }}>
                <div style={{ ...ui.card, textAlign: "center", padding: 28 }}>
                    <Heart size={36} aria-hidden="true" style={{ color: "var(--color-primary)" }} />
                    <h1 style={{ ...ui.h1, marginTop: 12 }}>Obrigado por compartilhar.</h1>
                    <p style={{ ...ui.sub, fontSize: 16 }}>
                        Suas respostas vão ajudar a entender melhor o que as pessoas vivem e a melhorar o que importa. Você já pode fechar esta página.
                    </p>
                </div>
            </div>
        </PublicLayout>
    );
}
