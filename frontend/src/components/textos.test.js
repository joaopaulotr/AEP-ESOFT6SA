import { describe, expect, it, vi } from "vitest";

vi.mock("../services/api", () => ({ api: {}, ApiError: class extends Error {} }));

const { baseadoEm } = await import("./ScriptSynthesis");
const { linkSoLocal } = await import("./InviteModal");

describe("baseadoEm", () => {
    it("número, com singular e plural", () => {
        expect(baseadoEm(1)).toBe("Baseado em 1 entrevista");
        expect(baseadoEm(3)).toBe("Baseado em 3 entrevistas");
        expect(baseadoEm(0)).toBe("Baseado em 0 entrevistas");
    });

    it("aceita a lista antiga e valor ausente", () => {
        expect(baseadoEm(["a", "b"])).toBe("Baseado em 2 entrevistas");
        expect(baseadoEm(undefined)).toBe("Baseado em 0 entrevistas");
    });
});

describe("linkSoLocal", () => {
    it("localhost e 127.0.0.1 só abrem neste computador", () => {
        expect(linkSoLocal("http://localhost:5173/e/abc")).toBe(true);
        expect(linkSoLocal("http://127.0.0.1:5190/e/abc")).toBe(true);
    });

    it("domínio público e texto inválido não avisam", () => {
        expect(linkSoLocal("https://aep.exemplo.com.br/e/abc")).toBe(false);
        expect(linkSoLocal("não é url")).toBe(false);
    });
});
