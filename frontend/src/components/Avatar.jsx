import { useEffect, useRef } from "react";

const CORES = {
    ouvindo: "var(--color-listening)",
    pensando: "var(--color-thinking)",
    falando: "var(--color-speaking)",
};

const ROTULOS = {
    ouvindo: "Entrevistadora ouvindo você",
    pensando: "Entrevistadora pensando",
    falando: "Entrevistadora falando",
    parado: "Entrevistadora aguardando",
};

export default function Avatar({ size = 64, style: extraStyle, ativo = true, estado, nivelRef }) {
    const orbRef = useRef(null);
    const anelRef = useRef(null);
    const reagindo = estado === "ouvindo" || estado === "falando";

    useEffect(() => {
        if (!reagindo) return undefined;
        const reduzido = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
        if (reduzido) return undefined;

        const orb = orbRef.current;
        let raf = 0;
        let atual = 0;
        function quadro(t) {
            const bruto = nivelRef ? nivelRef.current : 0;
            const alvo =
                typeof bruto === "number"
                    ? Math.min(1, bruto * (estado === "ouvindo" ? 9 : 5))
                    : 0.35 + 0.25 * Math.abs(Math.sin(t / 210) * Math.sin(t / 530)); // sem medida ainda
            atual += (alvo - atual) * 0.25; // suaviza
            if (orb) orb.style.transform = `scale(${1 + atual * 0.08})`;
            if (anelRef.current) {
                anelRef.current.style.transform = `scale(${1.08 + atual * 0.3})`;
                anelRef.current.style.opacity = String(0.35 + atual * 0.65);
            }
            raf = requestAnimationFrame(quadro);
        }
        raf = requestAnimationFrame(quadro);
        return () => {
            cancelAnimationFrame(raf);
            if (orb) orb.style.transform = "";
        };
    }, [reagindo, estado, nivelRef]);


    const comOndas = estado === undefined && ativo;
    const cor = CORES[estado];

    return (
        <>
            <style>{`
                @keyframes onda {
                    0% {
                        transform: translate(-50%, -50%) scale(1);
                        opacity: 0.6;
                    }
                    100% {
                        transform: translate(-50%, -50%) scale(1.4);
                        opacity: 0;
                    }
                }
                @keyframes avatar-gira {
                    to { transform: rotate(360deg); }
                }
                @keyframes avatar-respira {
                    0%, 100% { transform: scale(0.97); }
                    50% { transform: scale(1.03); }
                }
                @media (prefers-reduced-motion: reduce) {
                    .avatar-onda { animation: none !important; opacity: 0.35; }
                    .avatar-anim { animation: none !important; }
                }
            `}</style>
            <div
                role={estado ? "img" : undefined}
                aria-label={estado ? ROTULOS[estado] ?? ROTULOS.parado : undefined}
                style={{
                    position: "relative",
                    width: size,
                    height: size,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    ...extraStyle,
                }}
            >
                {comOndas && <div className="avatar-onda" style={ondaStyle(size, "0s")} />}
                {comOndas && <div className="avatar-onda" style={ondaStyle(size, "1s")} />}

                {/* Ouvindo / falando: anel que reage ao volume */}
                {reagindo && (
                    <div
                        ref={anelRef}
                        style={{
                            position: "absolute",
                            inset: 0,
                            borderRadius: "50%",
                            border: `3px solid ${cor}`,
                            boxShadow: `0 0 24px ${cor}`,
                            transform: "scale(1.08)",
                            opacity: 0.5,
                        }}
                    />
                )}

                {/* Pensando: anel tracejado girando */}
                {estado === "pensando" && (
                    <div
                        className="avatar-anim"
                        style={{
                            position: "absolute",
                            inset: -8,
                            borderRadius: "50%",
                            border: `2px dashed ${cor}`,
                            animation: "avatar-gira 3s linear infinite",
                        }}
                    />
                )}

                <div
                    ref={orbRef}
                    className="avatar-anim"
                    style={{
                        position: "relative",
                        width: size,
                        height: size,
                        borderRadius: "50%",
                        boxShadow: "0px 12px 24px rgba(127, 168, 159, 0.25)",
                        background: `
                            radial-gradient(circle at left center, #e69113cb, transparent 50%),
                            radial-gradient(circle at center, #ffffff, transparent 50%),
                            radial-gradient(circle at center top, #F87060, transparent 70%),
                            radial-gradient(circle at center bottom, #a0c9ca, transparent 55%),
                            #f1faff
                        `,
                        animation: estado === "pensando" ? "avatar-respira 1.6s ease-in-out infinite" : "none",
                        willChange: reagindo ? "transform" : undefined,
                    }}
                />
            </div>
        </>
    );
}

function ondaStyle(size, delay) {
    return {
        position: "absolute",
        top: "50%",
        left: "50%",
        width: size,
        height: size,
        borderRadius: "50%",
        border: "1px solid #98d3c67e",
        animation: "onda 3s ease-out infinite",
        animationDelay: delay,
    };
}