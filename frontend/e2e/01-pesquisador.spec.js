import { test, expect } from "@playwright/test";

test("pesquisador: roteiros do seed, entrevistas concluídas, transcrição e síntese com citação", async ({ page }) => {
    await page.goto("/entrevistas");
    await expect(page.getByRole("heading", { name: "Entrevistas", level: 1 })).toBeVisible();
    for (const titulo of [
        "Transporte público na periferia",
        "Acesso à saúde básica (UBS)",
        "Trabalho por aplicativo",
        "Entrevista generalista",
    ]) {
        await expect(page.getByRole("heading", { name: titulo, level: 2 })).toBeVisible();
    }
    await expect(page.getByRole("heading", { level: 2 })).toHaveCount(4);

    const card = page.getByRole("article").filter({ hasText: "Transporte público na periferia" });
    await card.getByRole("button", { name: "Ver entrevistas" }).click();
    await expect(page.getByRole("heading", { name: "Transporte público na periferia", level: 1 })).toBeVisible();

    const itens = page.getByRole("list").getByRole("button");
    await expect(itens).not.toHaveCount(0);

    await page.getByRole("button", { name: "Concluídas" }).click();
    await expect(page.getByRole("button", { name: "Concluídas" })).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByRole("list").getByText("Concluída", { exact: true }).first()).toBeVisible();
    await expect(page.getByRole("list").getByText("Em andamento")).toHaveCount(0);

    await page.getByRole("button", { name: /Dona Sônia/ }).click();
    await expect(page.getByRole("heading", { name: "Conversa" })).toBeVisible();
    await expect(page.getByText("Esperei o ônibus quarenta minutos no ponto").first()).toBeVisible();

    const sintese = page.getByRole("region", { name: "Síntese" });
    await expect(sintese).toBeVisible();
    await expect(sintese.locator("blockquote").first()).toContainText("Esperei o ônibus quarenta minutos no ponto");
});
