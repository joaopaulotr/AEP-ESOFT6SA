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
            if (typeof body.detail === "string") {
                detail = body.detail;
            } else if (Array.isArray(body.detail)) {
                detail = body.detail
                    .map((d) => (typeof d?.msg === "string" ? d.msg : ""))
                    .filter(Boolean)
                    .join("; ");
            }
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

    /** Convite público (sem login): só o que a pessoa convidada precisa ver. */
    async getPublicInvite(slug) {
        const res = await request(`/convite/${encodeURIComponent(slug)}`);
        return res.json();
    },

    /** Cria participante + sessão pelo convite. Devolve {session_id, pergunta, titulo, ...}. */
    async startFromInvite(slug, data) {
        const res = await request(`/convite/${encodeURIComponent(slug)}/sessao`, postJson(data));
        return res.json();
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

    /**
     * Turno em streaming (SSE sobre POST). Devolve a Response já validada (404/409 viram ApiError);
     * quem chama lê `res.body` (ver useTurnStream). `signal` aborta a leitura.
     */
    async streamTurn(sessionId, texto, { signal } = {}) {
        return request(`/turn/${sessionId}/stream`, { ...postJson({ texto }), signal });
    },

    /** Encerra a sessão manualmente (botão "Concluir"). */
    async finishSession(sessionId) {
        await request(`/session/${sessionId}/finish`, { method: "POST" });
    },

    /** `tom`: "acolhedor" | "neutro" | "formal" (tom da persona do roteiro); omitido = padrão do servidor. */
    async synthesizeSpeech(texto, tom) {
        const res = await request("/voice/fala", postJson(tom ? { texto, tom } : { texto }));
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

    async getDashboard(scriptId) {
        const res = await request(`/scripts/${encodeURIComponent(scriptId)}/painel`);
        return res.json();
    },

    /** Relatório cruzado salvo do roteiro; null se ainda não foi gerado (404). */
    async getScriptSynthesis(scriptId) {
        try {
            const res = await request(`/scripts/${encodeURIComponent(scriptId)}/sintese`);
            return await res.json();
        } catch (e) {
            if (e instanceof ApiError && e.status === 404) return null;
            throw e;
        }
    },

    async generateScriptSynthesis(scriptId, { refresh = false } = {}) {
        const qs = refresh ? "?refresh=true" : "";
        const res = await request(`/scripts/${encodeURIComponent(scriptId)}/sintese${qs}`, { method: "POST" });
        return res.json();
    },
};
