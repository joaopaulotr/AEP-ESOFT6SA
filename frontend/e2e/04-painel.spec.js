import { test, expect } from "@playwright/test";

test("painel: cartões, gráficos, tabela de dados e relatório do roteiro", async ({ page }) => {
    await page.goto("/entrevistas");
    await page.getByRole("button", { name: "Painel do roteiro Transporte público na periferia" }).click();

    await expect(page.getByRole("heading", { name: "Painel: Transporte público na periferia" })).toBeVisible();
    for (const rotulo of ["Entrevistas", "Taxa de conclusão", "Duração média", "Custo médio"]) {
        await expect(page.getByText(rotulo, { exact: true }).first()).toBeVisible();
    }
    const cartoes = page.locator(".painel-tiles > div");
    await expect(cartoes).toHaveCount(4);
    await expect(cartoes.nth(0)).toContainText(/\d+/);
    await expect(cartoes.nth(1)).toContainText(/\d+\s?%/);

    for (const titulo of ["O que a entrevistadora fez", "Aprofundamentos por pergunta", "Temas mais citados", "Canais", "Entrevistas por dia"]) {
        await expect(page.getByRole("heading", { name: titulo, level: 3 })).toBeVisible();
    }

    const figura = page.getByRole("figure").filter({ has: page.getByRole("heading", { name: "Canais", level: 3 }) });
    await figura.getByRole("button", { name: "Ver dados" }).click();
    await expect(figura.getByRole("table")).toBeVisible();
    await expect(figura.getByRole("button", { name: "Ocultar dados" })).toBeVisible();

    // Relatório do roteiro: já existe no seed ou é gerado agora.
    const relatorio = page.getByRole("region", { name: "Relatório do roteiro" });
    await expect(relatorio).toBeVisible();
    const gerar = relatorio.getByRole("button", { name: "Gerar relatório" });
    const gerarDeNovo = relatorio.getByRole("button", { name: "Gerar de novo" });
    await expect(gerar.or(gerarDeNovo)).toBeVisible();
    if (await gerar.isVisible()) await gerar.click();
    await expect(gerarDeNovo).toBeVisible();
    await expect(relatorio.getByText(/Baseado em \d+ entrevistas/)).toBeVisible();
});
