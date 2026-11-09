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
