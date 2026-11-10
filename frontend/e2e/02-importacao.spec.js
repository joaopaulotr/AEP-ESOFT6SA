import { test, expect } from "@playwright/test";
import { TITULO_IMPORTADO } from "./helpers";

test("importação: subir questionário, revisar no editor, publicar e ver na lista", async ({ page }) => {
    await page.goto("/entrevistas");
    await page.getByRole("button", { name: "Subir questionário" }).click();
    await expect(page.getByRole("heading", { name: "Subir questionário", level: 1 })).toBeVisible();

    await page.getByLabel("Arquivo do questionário").setInputFiles("e2e/fixtures/questionario.txt");

    await expect(page).toHaveURL(/\/roteiros\/novo$/);
    await expect(page.getByText("Revise as perguntas antes de publicar.")).toBeVisible();
    await expect(page.getByLabel("Título")).not.toHaveValue("");
    await expect(page.getByText("Como é o seu dia a dia no bairro onde você mora?")).toBeVisible();

    await page.getByLabel("Título").fill(TITULO_IMPORTADO);
    await page.getByRole("button", { name: "Publicar" }).click();

    await expect(page).toHaveURL(/\/entrevistas$/);
    await expect(page.getByRole("heading", { name: TITULO_IMPORTADO, level: 2 })).toBeVisible();
    await expect(page.getByRole("heading", { level: 2 })).toHaveCount(5);
});
