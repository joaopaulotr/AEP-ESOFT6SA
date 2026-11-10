import { test, expect } from "@playwright/test";
import { tituloUnico, criarRoteiro, entrarPorTexto, responder } from "./helpers";

// Cria o próprio roteiro (título único) pela API: independe dos outros cenários e de tentativas anteriores.
test("convite + modo texto: responde tudo, agradecimento, entrevista concluída e síntese", async ({ page, request }) => {
    const titulo = tituloUnico("Roteiro do convite (E2E)");
    await criarRoteiro(request, titulo, [
        "Como é o seu dia a dia no bairro onde você mora?",
        "Qual foi a última vez que você precisou de um serviço público e como foi?",
        "O que você mudaria no bairro se pudesse?",
    ]);
    await page.goto("/entrevistas");
    const card = page.getByRole("article").filter({ hasText: titulo });
    await expect(card.getByText(/0 concluídas/)).toBeVisible();
    await card.getByRole("button", { name: /Convidar para/ }).click();

    const modal = page.getByRole("dialog");
    await expect(modal).toBeVisible();
    await expect(modal.getByRole("button", { name: "Copiar link" })).toBeVisible();
    await expect(modal.getByRole("img", { name: /QR code do convite/ })).toBeVisible();
    const link = await modal.getByRole("link", { name: "Abrir convite" }).getAttribute("href");
    expect(link).toMatch(/\/e\/.+/);
    await modal.getByRole("button", { name: "Fechar" }).click();

    await entrarPorTexto(page, link, { apelido: "Marta" });
    const respostas = [
        "Acordo cedo e pego ônibus lotado todos os dias.",
        "Fui ao posto de saúde mês passado e esperei muito tempo.",
        "Eu colocaria mais iluminação nas ruas.",
    ];
    for (const r of respostas) await responder(page, r);

    await expect(page).toHaveURL(/\/e\/[^/]+\/obrigado(?:\?.*)?$/);
    await expect(page.getByRole("heading", { name: "Obrigado por compartilhar." })).toBeVisible();

    // Pesquisador: a entrevista aparece como concluída e a síntese é gerada.
    await page.goto("/entrevistas");
    const cardDepois = page.getByRole("article").filter({ hasText: titulo });
    await expect(cardDepois.getByText(/1 concluída/)).toBeVisible();
    await cardDepois.getByRole("button", { name: "Ver entrevistas" }).click();
    await page.getByRole("button", { name: "Concluídas" }).click();
    await page.getByRole("button", { name: /Marta/ }).click();

    await expect(page.getByText(respostas[0]).first()).toBeVisible();
    await page.getByRole("button", { name: "Gerar síntese" }).click();
    const sintese = page.getByRole("region", { name: "Síntese" });
    await expect(sintese.locator("blockquote").first()).toContainText(respostas[0]);
});
