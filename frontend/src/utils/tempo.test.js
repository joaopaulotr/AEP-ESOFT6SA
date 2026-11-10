import { describe, expect, it } from "vitest";
import { atrasoDePensar, estimativaMinutos, mmss } from "./tempo";

const fixo = (v) => () => v;

describe("atrasoDePensar", () => {
    it("resposta curta fica no piso de 600 ms (sem jitter)", () => {
        expect(atrasoDePensar(0, fixo(0.5))).toBe(600);
    });

    it("cresce com o tamanho da resposta (12 ms por caractere)", () => {
        expect(atrasoDePensar(50, fixo(0.5))).toBe(1200);
        expect(atrasoDePensar(100, fixo(0.5))).toBe(1800);
    });

    it("respostas longas param no teto de 2,5 s", () => {
        expect(atrasoDePensar(10_000, fixo(0.5))).toBe(2500);
    });

    it("jitter de ±250 ms, sem sair de 600..2500", () => {
        expect(atrasoDePensar(50, fixo(1))).toBe(1450);
        expect(atrasoDePensar(50, fixo(0))).toBe(950);
        expect(atrasoDePensar(0, fixo(0))).toBe(600);
        expect(atrasoDePensar(10_000, fixo(1))).toBe(2500);
    });
});

describe("estimativaMinutos", () => {
    it("2 minutos por pergunta", () => {
        expect(estimativaMinutos(5)).toBe(10);
        expect(estimativaMinutos(1)).toBe(2);
    });

    it("sem número válido assume 1 pergunta", () => {
        expect(estimativaMinutos(0)).toBe(2);
        expect(estimativaMinutos(undefined)).toBe(2);
    });
});

describe("mmss", () => {
    it("formata segundos", () => {
        expect(mmss(0)).toBe("00:00");
        expect(mmss(125)).toBe("02:05");
    });
});
