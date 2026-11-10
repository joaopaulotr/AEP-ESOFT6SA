import { expect } from "@playwright/test";

export const API = "http://127.0.0.1:8090/api/v1";
export const TITULO_IMPORTADO = "Questionário do bairro (E2E)";

/** Cria um roteiro pela API (isola os cenários entre si) e devolve { script_id, link_convite, titulo }. */
export async function criarRoteiro(request, titulo, perguntas) {
    const resp = await request.post(`${API}/scripts`, {
        data: { titulo, perguntas: perguntas.map((texto) => ({ texto })) },
    });
    expect(resp.ok()).toBeTruthy();
    const { script_id: scriptId } = await resp.json();
    const lista = await (await request.get(`${API}/scripts`)).json();
    const roteiro = lista.find((r) => r.script_id === scriptId);
    return { script_id: scriptId, link_convite: roteiro.link_convite, titulo };
}

/** Entra no convite pelo modo texto e começa a entrevista. */
export async function entrarPorTexto(page, link, { apelido } = {}) {
    await page.goto(link);
    await page.getByRole("button", { name: "Escrever" }).click();
    if (apelido) await page.getByLabel(/Como prefere ser chamado/i).fill(apelido);
    await page.getByRole("button", { name: "Começar" }).click();
    await expect(page).toHaveURL(/\/e\/[^/]+\/entrevista(?:\?.*)?$/);
}

/** Responde uma pergunta no modo texto, esperando o campo liberar (turno da pessoa). */
export async function responder(page, texto) {
    const campo = page.getByLabel("Sua resposta");
    await expect(campo).toBeEnabled();
    await campo.fill(texto);
    await page.getByRole("button", { name: "Enviar resposta" }).click();
    await expect(page.getByRole("log", { name: "Conversa da entrevista" })).toContainText(texto);
}
