import { describe, expect, it, vi } from "vitest";

vi.mock("../services/api", () => ({ api: {} })); // os hooks importam o client; aqui só as funções puras

const { pausaApos, atrasoDoCaractere } = await import("./useTypewriter");
const { sortear, fillerPermitido, FRASES_FILLER, PROBABILIDADE_FILLER } = await import("./useFillers");
const { lerEventosSSE } = await import("./useTurnStream");

const fixo = (v) => () => v;
/** Gerador que devolve os valores em sequência. */
const seq = (...vals) => {
    let i = 0;
    return () => vals[i++];
};

describe("pausaApos", () => {
    it("pausa leve (250-450 ms) em , ; :", () => {
        for (const ch of [",", ";", ":"]) {
            expect(pausaApos(ch, fixo(0))).toBe(250);
            expect(pausaApos(ch, fixo(1))).toBe(450);
        }
    });

    it("pausa forte (400-700 ms) em . ? ! …", () => {
        for (const ch of [".", "?", "!", "…"]) {
            expect(pausaApos(ch, fixo(0))).toBe(400);
            expect(pausaApos(ch, fixo(1))).toBe(700);
        }
    });

    it("letra comum não pausa", () => {
        expect(pausaApos("a", fixo(0.5))).toBe(0);
        expect(pausaApos(" ", fixo(0.5))).toBe(0);
    });
});

describe("atrasoDoCaractere", () => {
    it("1000/cps com jitter de ±30%", () => {
        expect(atrasoDoCaractere(50, fixo(0))).toBeCloseTo(14);
        expect(atrasoDoCaractere(50, fixo(1))).toBeCloseTo(26);
    });
});

describe("sortear (filler)", () => {
    it("só sons neutros curtos", () => {
        expect(FRASES_FILLER).toEqual(["Hmm…", "Certo…", "Aham…", "Entendi…"]);
    });

    it("sem sorte (>= probabilidade) não toca", () => {
        expect(sortear(FRASES_FILLER, null, fixo(PROBABILIDADE_FILLER))).toBeNull();
    });

    it("nunca repete o último", () => {
        expect(sortear(["Hmm…", "Certo…"], "Hmm…", seq(0, 0))).toBe("Certo…");
    });

    it("sem candidato pronto devolve null", () => {
        expect(sortear([], null, fixo(0))).toBeNull();
        expect(sortear(["Hmm…"], "Hmm…", fixo(0))).toBeNull();
    });

    it("escolhe pelo segundo sorteio", () => {
        expect(sortear(FRASES_FILLER, null, seq(0, 0.99))).toBe("Entendi…");
    });
});

describe("fillerPermitido", () => {
    it("só sem risco", () => {
        expect(fillerPermitido({ risco: "nenhum" })).toBe(true);
        expect(fillerPermitido({})).toBe(true);
        expect(fillerPermitido(undefined)).toBe(true);
        expect(fillerPermitido({ risco: "sofrimento" })).toBe(false);
        expect(fillerPermitido({ risco: "pedido_parar" })).toBe(false);
    });
});

/** Corpo de stream que entrega os pedaços (bytes) exatamente como recebidos. */
function corpo(pedacos) {
    let i = 0;
    return {
        getReader: () => ({
            read: async () => (i < pedacos.length ? { done: false, value: pedacos[i++] } : { done: true, value: undefined }),
        }),
    };
}
const bytes = (texto) => new TextEncoder().encode(texto);

async function coletar(pedacos, opcoes) {
    const eventos = [];
    await lerEventosSSE(corpo(pedacos), (evento, dados) => eventos.push([evento, dados]), opcoes);
    return eventos;
}

describe("lerEventosSSE", () => {
    it("lê vários eventos de um pedaço só", async () => {
        const ev = await coletar([bytes('event: pensando\ndata: {"risco":"nenhum"}\n\nevent: fim\ndata: {"fala":"Oi"}\n\n')]);
        expect(ev).toEqual([["pensando", { risco: "nenhum" }], ["fim", { fala: "Oi" }]]);
    });

    it("junta evento cortado em qualquer ponto (inclusive entre os dois \\n)", async () => {
        const texto = 'event: frase\ndata: {"texto":"Olá"}\n\n';
        for (let corte = 1; corte < texto.length; corte += 1) {
            const ev = await coletar([bytes(texto.slice(0, corte)), bytes(texto.slice(corte))]);
            expect(ev).toEqual([["frase", { texto: "Olá" }]]);
        }
    });

    it("caractere UTF-8 dividido entre dois pedaços", async () => {
        const b = bytes('event: frase\ndata: {"texto":"ação…"}\n\n');
        const i = b.indexOf(0xc3) + 1; // no meio do "ç"
        const ev = await coletar([b.slice(0, i), b.slice(i)]);
        expect(ev).toEqual([["frase", { texto: "ação…" }]]);
    });

    it("aceita \\r\\n, ignora comentário/keep-alive e bloco malformado", async () => {
        const ev = await coletar([bytes(': keep-alive\r\n\r\nevent: frase\r\ndata: {quebrado\r\n\r\nevent: fim\r'), bytes('\ndata: {"ok":true}\r\n\r\n')]);
        expect(ev).toEqual([["fim", { ok: true }]]);
    });

    it("último bloco sem linha em branco no fim também sai", async () => {
        const ev = await coletar([bytes('event: fim\ndata: {"fala":"tchau"}')]);
        expect(ev).toEqual([["fim", { fala: "tchau" }]]);
    });

    it("avisa cada pedaço lido (vigia de inatividade)", async () => {
        const aoPedaco = vi.fn();
        await coletar([bytes(": ping\n\n"), bytes(": ping\n\n")], { aoPedaco });
        expect(aoPedaco).toHaveBeenCalledTimes(3); // 2 pedaços + o fim
    });
});
