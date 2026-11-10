import { useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { Heart } from "lucide-react";
import PublicLayout from "../components/PublicLayout";
import CvvAviso from "../components/CvvAviso";
import { api } from "../services/api";
import { lerSessaoPublica } from "../utils/sessaoPublica";
import { ui } from "../styles/ui";

/**
 * Agradecimento. Se a entrevista terminou em acolhimento, repete o cartão do CVV: vem no state da
 * navegação ou, ao recarregar, da rota pública da sessão (id guardado no sessionStorage).
 */
export default function ThankYouScreen() {
    const { slug } = useParams();
    const location = useLocation();
    const doEstado = location.state?.acolhimento;
    const [acolhimento, setAcolhimento] = useState(doEstado === true);

    useEffect(() => {
        if (typeof doEstado === "boolean") return undefined;
        const guardada = lerSessaoPublica(slug);
        if (!guardada) return undefined;
        let vivo = true;
        api.getPublicSession(slug, guardada.sessionId)
            .then((est) => { if (vivo && est?.acolhimento) setAcolhimento(true); })
            .catch(() => {});
        return () => { vivo = false; };
    }, [slug, doEstado]);

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
                {acolhimento && <div style={{ marginTop: 16 }}><CvvAviso /></div>}
            </div>
        </PublicLayout>
    );
}
