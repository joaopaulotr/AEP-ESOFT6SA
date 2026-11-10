import { test, expect } from "@playwright/test";
import { tituloUnico, criarRoteiro, entrarPorTexto, responder } from "./helpers";

test("convite inexistente mostra a mensagem de convite encerrado", async ({ page }) => {
    await page.goto("/e/nao-existe-e2e");
    await expect(page.getByText("Esse convite não existe ou foi encerrado.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Começar" })).toHaveCount(0);
});

test("pedido de parar no modo texto encerra com a mensagem de parada", async ({ page, request }) => {
    const roteiro = await criarRoteiro(request, tituloUnico("Roteiro de parada (E2E)"), [
        "Como é o seu dia a dia?",
        "O que você mudaria no bairro?",
    ]);
    await entrarPorTexto(page, roteiro.link_convite);
    await responder(page, "quero parar");

    await expect(page.getByRole("log", { name: "Conversa da entrevista" }))
        .toContainText("Tudo bem, vamos parar por aqui. Obrigado por ter conversado comigo.");
    await expect(page).toHaveURL(/\/e\/[^/]+\/obrigado(?:\?.*)?$/);
});
