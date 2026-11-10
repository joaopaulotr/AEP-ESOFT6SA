import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, RefreshCw } from "lucide-react";
import SideBar from "../components/SideBar";
import FileDrop from "../components/FileDrop";
import { api } from "../services/api";
import { ui, CSS } from "../styles/ui";
import { guardarRascunho } from "./ScriptEditorScreen";

export default function ScriptImportScreen() {
    const navigate = useNavigate();
    const [lendo, setLendo] = useState(false);
    const [erro, setErro] = useState("");

    async function enviar(file) {
        setErro("");
        setLendo(true);
        try {
            const rascunho = await api.uploadQuestionnaire(file);
            guardarRascunho(rascunho);
            navigate("/roteiros/novo", { state: { rascunho } });
        } catch (e) {
            setErro(e.detail || "Não consegui ler o arquivo. Tente de novo.");
            setLendo(false);
        }
    }

    return (
        <SideBar>
            <div style={ui.page}>
                <style>{CSS}</style>
                <button className="ui-btn" style={ui.voltar} onClick={() => navigate("/entrevistas")}>
                    <ArrowLeft size={16} aria-hidden="true" /> Voltar
                </button>
                <h1 style={ui.h1}>Subir questionário</h1>
                <p style={ui.sub}>Envie um arquivo com as perguntas. Você poderá revisar tudo antes de publicar.</p>
                <div style={{ marginTop: 20 }}>
                    <FileDrop onFile={enviar} desabilitado={lendo} />
                    {lendo && (
                        <p role="status" aria-live="polite" style={{ ...ui.estadoTexto, marginTop: 14, display: "flex", alignItems: "center", gap: 8 }}>
                            <RefreshCw size={18} className="girando" aria-hidden="true" /> Lendo o arquivo…
                        </p>
                    )}
                    {erro && <p role="alert" style={{ color: "var(--color-error)", marginTop: 14 }}>{erro}</p>}
                </div>
            </div>
        </SideBar>
    );
}
