/** Hora atual no formato "14:05". */
export function agora() {
    return new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

/** Segundos → "mm:ss". */
export function mmss(s) {
    const m = String(Math.floor(s / 60)).padStart(2, "0");
    const seg = String(s % 60).padStart(2, "0");
    return `${m}:${seg}`;
}

const FORMATO_DATA = new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Sao_Paulo",
    dateStyle: "short",
    timeStyle: "short",
});

/** Data ISO da API → "09/11/2026 14:05" (fuso de São Paulo). */
export function dataHora(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? "" : FORMATO_DATA.format(d);
}

/**
 * Atraso de "pensar" antes da 1ª frase da IA tocar: proporcional ao tamanho da resposta da pessoa,
 * 600 ms a 2,5 s, com jitter de +-250 ms (o resultado também fica dentro de 600 ms..2,5 s).
 */
export function atrasoDePensar(tamanhoResposta, aleatorio = Math.random) {
    const base = Math.min(2500, Math.max(600, 600 + tamanhoResposta * 12));
    const jitter = (aleatorio() * 2 - 1) * 250;
    return Math.round(Math.min(2500, Math.max(600, base + jitter)));
}
