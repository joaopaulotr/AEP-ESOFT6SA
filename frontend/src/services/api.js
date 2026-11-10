const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const API_PREFIX = "/api/v1";

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
    
    async createSession({ scriptId, participantId } = {}) {
        const body = {};
        if (scriptId) body.script_id = scriptId;
        if (participantId) body.participant_id = participantId;
        const res = await request("/session", postJson(body));
        return res.json();
    },

    async listScripts() {
        const res = await request("/scripts");
        return res.json();
    },

    async getScript(scriptId) {
        const res = await request(`/scripts/${encodeURIComponent(scriptId)}`);
        return res.json();
    },

    /** Envia o questionário; devolve um rascunho de roteiro (não grava nada). */
    async uploadQuestionnaire(file) {
        const form = new FormData();
        form.append("file", file); // sem Content-Type manual: o browser define o boundary
        const res = await request("/scripts/upload", { method: "POST", body: form });
        return res.json();
    },

    async createScript(data) {
        const res = await request("/scripts", postJson(data));
        return res.json();
    },

    async updateScript(scriptId, data) {
        const res = await request(`/scripts/${encodeURIComponent(scriptId)}`, { ...postJson(data), method: "PUT" });
        return res.json();
    },

    async deleteScript(scriptId) {
        await request(`/scripts/${encodeURIComponent(scriptId)}`, { method: "DELETE" });
    },

    async getInvite(scriptId) {
        const res = await request(`/scripts/${encodeURIComponent(scriptId)}/convite`);
        return res.json();
    },

    /** URL absoluta do QR Code (SVG), para usar direto em <img src>. */
    qrCodeUrl(scriptId) {
        return `${BASE_URL}${API_PREFIX}/scripts/${encodeURIComponent(scriptId)}/qrcode.svg`;
    },

    async listScriptSessions(scriptId, { status } = {}) {
        const qs = status ? `?status=${encodeURIComponent(status)}` : "";
        const res = await request(`/scripts/${encodeURIComponent(scriptId)}/sessions${qs}`);
        return res.json();
    },

    async getSessionDetails(sessionId) {
        const res = await request(`/session/${sessionId}/detalhes`);
        return res.json();
    },

    /** Síntese salva da sessão; devolve null se ainda não foi gerada (404). */
    async getSynthesis(sessionId) {
        try {
            const res = await request(`/session/${sessionId}/synthesis`);
            return await res.json();
        } catch (e) {
            if (e instanceof ApiError && e.status === 404) return null;
            throw e;
        }
    },

    async deleteSession(sessionId) {
        await request(`/session/${sessionId}`, { method: "DELETE" });
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

    async generateSynthesis(sessionId, { refresh = false } = {}) {
        const qs = refresh ? "?refresh=true" : "";
        const res = await request(`/session/${sessionId}/synthesis${qs}`, { method: "POST" });
        return res.json();
    },
};
