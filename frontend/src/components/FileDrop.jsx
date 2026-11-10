import React, { useRef, useState } from "react";
import { UploadCloud } from "lucide-react";
import { ui } from "../styles/ui";

export const ACEITOS = ".txt,.md,.csv,.docx,.pdf";
export const MAX_BYTES = 2 * 1024 * 1024;

/** Área de arrastar ou escolher um arquivo. Valida extensão e tamanho (2 MB) antes de enviar. */
export default function FileDrop({ onFile, desabilitado = false }) {
    const inputRef = useRef(null);
    const [arrastando, setArrastando] = useState(false);
    const [erro, setErro] = useState("");

    function receber(file) {
        if (!file) return;
        const ext = `.${file.name.split(".").pop().toLowerCase()}`;
        if (!ACEITOS.split(",").includes(ext)) {
            setErro("Formato não aceito. Use .txt, .md, .csv, .docx ou .pdf.");
            return;
        }
        if (file.size > MAX_BYTES) {
            setErro("O arquivo é maior que 2 MB. Envie um arquivo menor.");
            return;
        }
        setErro("");
        onFile(file);
    }

    return (
        <div>
            <div
                onDragOver={(e) => { e.preventDefault(); setArrastando(true); }}
                onDragLeave={() => setArrastando(false)}
                onDrop={(e) => { e.preventDefault(); setArrastando(false); if (!desabilitado) receber(e.dataTransfer.files?.[0]); }}
                style={{
                    ...ui.card, display: "flex", flexDirection: "column", alignItems: "center", gap: 12,
                    padding: "32px 16px", textAlign: "center",
                    borderStyle: "dashed", borderWidth: 2,
                    borderColor: arrastando ? "var(--color-primary)" : "var(--color-primary-border)",
                }}
            >
                <UploadCloud size={32} aria-hidden="true" style={{ color: "var(--color-primary)" }} />
                <p style={{ ...ui.estadoTexto, color: "var(--color-text-2)" }}>Arraste o arquivo do questionário até aqui</p>
                <button type="button" className="ui-btn" style={ui.btnPrimario} disabled={desabilitado}
                    onClick={() => inputRef.current?.click()}>
                    Escolher arquivo
                </button>
                <p style={ui.meta}>Formatos: .txt, .md, .csv, .docx, .pdf · até 2 MB</p>
                <input ref={inputRef} type="file" accept={ACEITOS} hidden
                    aria-label="Arquivo do questionário"
                    onChange={(e) => { receber(e.target.files?.[0]); e.target.value = ""; }} />
            </div>
            {erro && <p role="alert" style={{ color: "var(--color-error)", fontSize: 14, marginTop: 10 }}>{erro}</p>}
        </div>
    );
}
