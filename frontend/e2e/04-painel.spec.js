import { test, expect } from "@playwright/test";

test("painel: cartões, gráficos, tabela de dados e relatório do roteiro", async ({ page }) => {
    await page.goto("/entrevistas");
    await page.getByRole("button", { name: "Painel do roteiro Transporte público na periferia" }).click();

    await expect(page.getByRole("heading", { name: "Painel: Transporte público na periferia" })).toBeVisible();
    // Cada cartão é um grupo com o nome do rótulo; o valor é o <strong> dele.
    const valorDe = (rotulo) => page.getByRole("group", { name: rotulo, exact: true }).locator("strong");
    await expect(valorDe("Entrevistas")).toHaveText(/^\d+$/);
    await expect(valorDe("Taxa de conclusão")).toHaveText(/^\d+\s?%$/);
    await expect(valorDe("Duração média")).toHaveText(/\d+([.,]\d+)?\s?min/);
    await expect(valorDe("Custo médio")).toHaveText(/\d|—/); // "—" quando nenhuma entrevista teve custo medido

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
    await expect(relatorio.getByText(/Baseado em \d+ entrevistas?/)).toBeVisible();
    await expect(relatorio.getByRole("heading", { name: "Relatório do roteiro" })).toBeVisible();
});
