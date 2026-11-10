import { test, expect } from "@playwright/test";
import { tituloUnico, criarRoteiro, entrarPorTexto, responder, vigiarConsole } from "./helpers";

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
    await expect(page.getByText(/fale com o CVV/)).toHaveCount(0); // parada comum: sem cartão do CVV
});

test("sofrimento no modo texto: cartão do CVV fica na tela até Continuar e se repete no agradecimento", async ({ page, request }) => {
    const erros = vigiarConsole(page);
    const roteiro = await criarRoteiro(request, tituloUnico("Roteiro de acolhimento (E2E)"), [
        "Como é o seu dia a dia?",
        "O que você mudaria no bairro?",
    ]);
    await entrarPorTexto(page, roteiro.link_convite);
    await expect(page).not.toHaveURL(/sessao=/); // o id da sessão não vai na URL
    await responder(page, "Ultimamente eu quero morrer.");

    const cvv = page.getByRole("region", { name: /Você não está sozinho/ });
    await expect(cvv).toContainText("Se precisar, fale com o CVV: ligue 188 (grátis, 24 h) ou acesse cvv.org.br");
    const continuar = cvv.getByRole("button", { name: "Continuar" });
    await expect(continuar).toBeEnabled();
    await expect(page.getByRole("button", { name: "Concluir" })).toBeDisabled();
    await expect(page.getByRole("button", { name: /Prefiro falar/ })).toBeDisabled();
    // Não sai sozinha da tela (antes saía em ~1,2 s).
    await page.waitForTimeout(2000);
    await expect(page).toHaveURL(/\/e\/[^/]+\/entrevista$/);

    await continuar.click();
    await expect(page).toHaveURL(/\/e\/[^/]+\/obrigado$/);
    await expect(page.getByText("Se precisar, fale com o CVV: ligue 188 (grátis, 24 h) ou acesse cvv.org.br")).toBeVisible();
    // Recarregar mantém o cartão.
    await page.reload();
    await expect(page.getByText("Se precisar, fale com o CVV: ligue 188 (grátis, 24 h) ou acesse cvv.org.br")).toBeVisible();
    expect(erros).toEqual([]);
});
