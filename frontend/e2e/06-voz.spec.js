import { test, expect } from "@playwright/test";
import { tituloUnico, criarRoteiro } from "./helpers";

// Fumaça: microfone falso aceito, a tela entra em "ouvindo" sem erro. Não valida o áudio.
test("voz: entra por Falar, o microfone falso é aceito e a tela mostra ouvindo", async ({ page, request }) => {
    const alertas = [];
    page.on("dialog", async (d) => {
        alertas.push(d.message());
        await d.dismiss();
    });

    const roteiro = await criarRoteiro(request, tituloUnico("Roteiro de voz (E2E)"), ["Como é o seu dia a dia?", "O que você mudaria?"]);
    await page.goto(roteiro.link_convite);
    await page.getByRole("button", { name: "Falar" }).click();
    await page.getByRole("button", { name: "Começar" }).click();
    await expect(page).toHaveURL(/\/e\/[^/]+\/entrevista(?:\?.*)?$/);

    const mic = page.getByRole("button", { name: "Falar ao microfone" });
    await expect(mic).toBeEnabled();
    await mic.click();

    await expect(page.getByRole("button", { name: "Parar e enviar resposta" })).toBeVisible();
    await expect(page.getByText("OUVINDO SUA RESPOSTA…")).toBeVisible();
    expect(alertas).toEqual([]);
});
