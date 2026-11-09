const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const API_PREFIX = "";

export class ApiError extends Error {

    constructor(status, path, detail = "") {
        super(detail || `Erro ${status} em ${path}`);
        this.name = "ApiError";
        this.status = status;
        this.path = path;
        this.detail = detail;
    }
}

async function request(path, options = {}) {
    const res = await fetch(`${BASE_URL}${API_PREFIX}${path}`, options);
    if (!res.ok) {
        let detail = "";
        try {
            const body = await res.json();
            detail = typeof body.detail === "string" ? body.detail : "";
        } catch {
        
        }
        throw new ApiError(res.status, path, detail);
    }
    return res;
}

function postJson(body) {
    return {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    };
}

export const api = {
    
    async createSession() {
        const res = await request("/session", { method: "POST" });
        return res.json();
    },

    async sendTurn(sessionId, texto) {
        const res = await request(`/turn/${sessionId}`, postJson({ texto }));
        return res.json();
    },

    /** Encerra a sessão manualmente (botão "Concluir"). */
    async finishSession(sessionId) {
        await request(`/session/${sessionId}/finish`, { method: "POST" });
    },

    async synthesizeSpeech(texto) {
        const res = await request("/voice/fala", postJson({ texto }));
        return res.blob();
    },

    async transcribeAudio(blob) {
        const form = new FormData();
        form.append("file", blob, "audio.webm");
        const res = await request("/voice/transcricao", { method: "POST", body: form });
        return res.json();
    },

    async generateSynthesis(sessionId) {
        const res = await request(`/session/${sessionId}/synthesis`, { method: "POST" });
        return res.json();
    },
};
