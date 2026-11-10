import { useEffect, useRef, useState } from "react";

const ROTULOS = {
    ouvindo: "Ouvindo você",
    pensando: "Pensando…",
    falando: "Falando",
    parado: "Aguardando",
};
const BARRAS = 24;
const LARGURA = 240;
const ALTURA = 56;

function useMovimentoReduzido() {
    const [reduzido, setReduzido] = useState(() => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false);
    useEffect(() => {
        const mq = window.matchMedia?.("(prefers-reduced-motion: reduce)");
        if (!mq) return undefined;
        const aoMudar = () => setReduzido(mq.matches);
        mq.addEventListener?.("change", aoMudar);
        return () => mq.removeEventListener?.("change", aoMudar);
    }, []);
    return reduzido;
}

/** Altura (0..1) de cada barra por estado. `nivel`: volume do microfone (RMS 0..1). */
function alturaDaBarra(estado, i, t, nivel) {
    if (estado === "ouvindo") {
        const ruido = 0.55 + 0.45 * Math.sin(t / 130 + i * 1.7);
        return 0.08 + Math.min(1, nivel * 9) * ruido * 0.92;
    }
    if (estado === "pensando") return 0.15 + 0.12 * (1 + Math.sin(t / 450 - i * 0.25)); // pulso suave
    if (estado === "falando") {
        // Aproximação: o áudio de saída não passa por um AnalyserNode (evita rotear a voz da IA
        // pelo AudioContext); o desenho imita a energia da fala.
        const env = 0.5 + 0.5 * Math.sin(t / 210 + i * 0.6) * Math.sin(t / 530 + i * 1.3);
        return 0.12 + 0.7 * Math.abs(env);
    }
    return 0.08;
}

/**
 * Onda de áudio em canvas: ouvindo (microfone), pensando (pulso suave), falando (saída).
 * Com `prefers-reduced-motion` desenha um quadro estático por estado. O rótulo em texto aparece
 * sempre, então o estado nunca depende só da animação.
 */
export default function Waveform({ estado = "parado", nivelRef }) {
    const canvasRef = useRef(null);
    const reduzido = useMovimentoReduzido();

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return undefined;
        const ctx = canvas.getContext("2d");
        const dpr = window.devicePixelRatio || 1;
        canvas.width = LARGURA * dpr;
        canvas.height = ALTURA * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        let raf = 0;
        let cores = null;
        let corLida = 0;

        function desenhar(t) {
            if (!cores || t - corLida > 500) {
                const css = getComputedStyle(canvas);
                cores = {
                    de: css.getPropertyValue("--color-wave-from").trim() || "#a0c9ca",
                    para: css.getPropertyValue("--color-wave-to").trim() || "#f87060",
                    ocioso: css.getPropertyValue("--color-wave-idle").trim() || "#39415f",
                };
                corLida = t;
            }
            ctx.clearRect(0, 0, LARGURA, ALTURA);
            const gradiente = ctx.createLinearGradient(0, 0, 0, ALTURA);
            gradiente.addColorStop(0, cores.de);
            gradiente.addColorStop(1, cores.para);
            ctx.fillStyle = estado === "parado" ? cores.ocioso : gradiente;

            const passo = LARGURA / BARRAS;
            const largura = Math.max(3, passo * 0.5);
            const nivel = nivelRef?.current ?? 0;
            for (let i = 0; i < BARRAS; i++) {
                const h = Math.max(4, alturaDaBarra(reduzido ? "parado" : estado, i, t, nivel) * ALTURA);
                const x = i * passo + (passo - largura) / 2;
                const y = (ALTURA - h) / 2;
                ctx.beginPath();
                ctx.roundRect ? ctx.roundRect(x, y, largura, h, largura / 2) : ctx.rect(x, y, largura, h);
                ctx.fill();
            }
        }

        if (reduzido || estado === "parado") {
            desenhar(0);
            return undefined;
        }
        function quadro(t) {
            desenhar(t);
            raf = requestAnimationFrame(quadro);
        }
        raf = requestAnimationFrame(quadro);
        return () => cancelAnimationFrame(raf);
    }, [estado, reduzido, nivelRef]);

    return (
        <div style={s.wrap}>
            <canvas ref={canvasRef} aria-hidden="true" style={s.canvas} />
            <span style={s.rotulo}>{ROTULOS[estado] ?? ROTULOS.parado}</span>
        </div>
    );
}

const s = {
    wrap: { display: "flex", flexDirection: "column", alignItems: "center", gap: 4, width: "100%" },
    canvas: { width: LARGURA, height: ALTURA, maxWidth: "100%" },
    rotulo: { fontSize: 13, fontWeight: 600, color: "var(--color-text-muted)" },
};
