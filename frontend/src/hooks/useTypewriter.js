import { useEffect, useRef, useState } from "react";

const PAUSA_LEVE = /[,;:]/;
const PAUSA_FORTE = /[.?!…]/;

/** Pausa (ms) depois de um caractere: 250-450 em , ; : e 400-700 em . ? ! … */
export function pausaApos(ch, aleatorio = Math.random) {
    if (PAUSA_LEVE.test(ch)) return 250 + aleatorio() * 200;
    if (PAUSA_FORTE.test(ch)) return 400 + aleatorio() * 300;
    return 0;
}

/** Tempo (ms) de um caractere para `cps` caracteres/s, com jitter de +-30%. */
export function atrasoDoCaractere(cps, aleatorio = Math.random) {
    return (1000 / cps) * (0.7 + aleatorio() * 0.6);
}

const reduzirMovimento = () =>
    typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/**
 * Revela frases uma a uma, anexando ao mesmo texto, no ritmo de quem digita (35-55 car./s por turno,
 * sem erros de digitação). `revelar` devolve uma Promise que resolve quando a frase termina (ou é
 * interrompida). Com prefers-reduced-motion cada frase aparece de uma vez (após o atraso inicial).
 */
export function useTypewriter() {
    const [texto, setTexto] = useState("");
    const acumuladoRef = useRef("");
    const timerRef = useRef(null);
    const acabarRef = useRef(null); // (mostrarTudo, atualizarTela) => encerra a frase em andamento
    const velocidadeRef = useRef(45);

    /** Sorteia a velocidade do turno. */
    function novoTurno() {
        velocidadeRef.current = 35 + Math.random() * 20;
    }

    /** Frase em andamento: mostra tudo agora (ex.: troca para voz) e libera a fila. */
    function concluirAgora() {
        acabarRef.current?.(true, true);
    }

    /** Interrompe sem mostrar o resto (erro, "Concluir", desmontagem). */
    function parar(atualizarTela = true) {
        acabarRef.current?.(false, atualizarTela);
    }

    function limpar() {
        acumuladoRef.current = "";
        setTexto("");
    }

    /** `depoisDe`: instante (Date.now) antes do qual nada aparece (atraso de "pensar"). */
    function revelar(frase, { depoisDe, instantaneo = false } = {}) {
        return new Promise((resolve) => {
            const base = acumuladoRef.current ? `${acumuladoRef.current} ` : "";
            const pausaEntreFrases = base ? pausaApos(base.trimEnd().slice(-1)) : 0;
            const mostrar = (n) => {
                acumuladoRef.current = base + frase.slice(0, n);
                setTexto(acumuladoRef.current);
            };
            const encerrar = (mostrarTudo, atualizarTela) => {
                clearTimeout(timerRef.current);
                timerRef.current = null;
                acabarRef.current = null;
                if (mostrarTudo) {
                    acumuladoRef.current = base + frase;
                    if (atualizarTela) setTexto(acumuladoRef.current);
                }
                resolve();
            };
            acabarRef.current = encerrar;

            const espera = depoisDe ? Math.max(0, depoisDe - Date.now()) : 0;
            if (instantaneo) {
                encerrar(true, true);
                return;
            }
            if (reduzirMovimento()) {
                timerRef.current = setTimeout(() => encerrar(true, true), espera);
                return;
            }
            let i = 0;
            const passo = () => {
                i += 1;
                mostrar(i);
                if (i >= frase.length) {
                    encerrar(false, false);
                    return;
                }
                timerRef.current = setTimeout(passo, atrasoDoCaractere(velocidadeRef.current) + pausaApos(frase[i - 1]));
            };
            timerRef.current = setTimeout(passo, Math.max(espera, pausaEntreFrases) + atrasoDoCaractere(velocidadeRef.current));
        });
    }

    // Só na desmontagem: interrompe a frase em andamento sem tocar no estado. `parar` lê apenas
    // refs (acabarRef), então a versão do 1º render serve; o exhaustive-deps não acusa este caso,
    // por isso não há eslint-disable aqui (um disable sem uso viraria aviso e o lint falharia).
    useEffect(() => () => parar(false), []);

    return { texto, revelar, novoTurno, concluirAgora, parar, limpar };
}
