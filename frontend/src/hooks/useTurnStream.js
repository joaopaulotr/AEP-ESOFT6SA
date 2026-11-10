import { useCallback, useEffect, useRef } from "react";
import { api } from "../services/api";

/**
 * Interpreta o corpo de um `text/event-stream`: blocos `event:`/`data:` separados por linha em
 * branco. O texto pode chegar cortado em qualquer ponto (no meio de uma linha, de um UTF-8 ou
 * entre o `\n` e o segundo `\n`), então o que sobra do último pedaço volta para o buffer.
 */
export async function lerEventosSSE(body, aoEvento, { aoPedaco } = {}) {
    const leitor = body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    function despachar(bloco) {
        let evento = "message";
        const dados = [];
        for (const linha of bloco.split("\n")) {
            if (!linha || linha.startsWith(":")) continue; // comentário / keep-alive
            const i = linha.indexOf(":");
            const campo = i === -1 ? linha : linha.slice(0, i);
            const valor = i === -1 ? "" : linha.slice(i + 1).replace(/^ /, "");
            if (campo === "event") evento = valor;
            else if (campo === "data") dados.push(valor);
        }
        if (!dados.length) return;
        let payload = {};
        try {
            payload = JSON.parse(dados.join("\n"));
        } catch {
            return; // bloco malformado: ignora, o próximo segue
        }
        aoEvento(evento, payload);
    }

    for (;;) {
        const { done, value } = await leitor.read();
        aoPedaco?.(); // qualquer byte (inclusive keep-alive) prova que a conexão está viva
        // Um \r solto no fim do pedaço fica no buffer até chegar o \n do próximo.
        buffer = (buffer + decoder.decode(value, { stream: !done })).replace(/\r\n/g, "\n");
        let fim;
        while ((fim = buffer.indexOf("\n\n")) !== -1) {
            despachar(buffer.slice(0, fim));
            buffer = buffer.slice(fim + 2);
        }
        if (done) break;
    }
    if (buffer.trim()) despachar(buffer);
}

export const INATIVIDADE_SSE_MS = 30000;
export const MSG_DEMOROU = "Demorou mais que o normal. Tente de novo.";

/**
 * `enviar(sessionId, texto, { onPensando, onFrase, onFim, onErro })` abre o turno em streaming e
 * resolve quando o stream acaba. Rejeita com ApiError se o servidor recusar antes de transmitir
 * (404/409) ou com o erro de rede. 30 s sem nenhum byte: aborta e rejeita com `detail` =
 * "Demorou mais que o normal…". `cancelar()` aborta (usado ao desmontar a tela).
 */
export function useTurnStream() {
    const controllerRef = useRef(null);

    const cancelar = useCallback(() => {
        controllerRef.current?.abort();
        controllerRef.current = null;
    }, []);

    const enviar = useCallback(async (sessionId, texto, { onPensando, onFrase, onFim, onErro } = {}) => {
        cancelar();
        const controller = new AbortController();
        controllerRef.current = controller;
        let estourou = false;
        let vigia = null;
        const rearmar = () => {
            clearTimeout(vigia);
            vigia = setTimeout(() => {
                estourou = true;
                controller.abort();
            }, INATIVIDADE_SSE_MS);
        };
        rearmar();
        try {
            const res = await api.streamTurn(sessionId, texto, { signal: controller.signal });
            await lerEventosSSE(res.body, (evento, dados) => {
                if (controller.signal.aborted) return;
                if (evento === "pensando") onPensando?.(dados);
                else if (evento === "frase") onFrase?.(dados);
                else if (evento === "fim") onFim?.(dados);
                else if (evento === "erro") onErro?.(dados);
            }, { aoPedaco: rearmar });
        } catch (e) {
            if (estourou) throw Object.assign(new Error(MSG_DEMOROU), { detail: MSG_DEMOROU });
            throw e;
        } finally {
            clearTimeout(vigia);
        }
    }, [cancelar]);

    useEffect(() => cancelar, [cancelar]);

    return { enviar, cancelar };
}
