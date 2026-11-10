import { test, expect } from "@playwright/test";
import { tituloUnico, criarRoteiro, vigiarConsole, coletarDialogos } from "./helpers";

// Microfone falso do Chromium (tom contínuo) + STT/TTS falsos do backend: valida o ciclo da tela
// (gravar → transcrição → confirmar → próxima fala), não a qualidade do áudio.
test("voz: grava, confirma o que foi entendido e recebe a próxima fala", async ({ page, request }) => {
    const erros = vigiarConsole(page);
    const dialogos = coletarDialogos(page);

    const roteiro = await criarRoteiro(request, tituloUnico("Roteiro de voz (E2E)"), ["Como é o seu dia a dia?", "O que você mudaria?"]);
    await page.goto(roteiro.link_convite);
    await page.getByRole("button", { name: "Falar" }).click();
    await page.getByRole("button", { name: "Começar" }).click();
    await expect(page).toHaveURL(/\/e\/[^/]+\/entrevista$/);

    const mic = page.getByRole("button", { name: "Falar ao microfone" });
    await expect(mic).toBeEnabled();
    await mic.click();
    await expect(page.getByText("OUVINDO SUA RESPOSTA…")).toBeVisible();
    await expect(page.getByText("Microfone ligado")).toHaveCount(0); // gravando: o botão de parar já diz tudo

    // O fim de fala automático (VAD) pode encerrar antes do clique: só clica se ainda estiver gravando.
    const parar = page.getByRole("button", { name: "Parar e enviar resposta" });
    if (await parar.isVisible()) await parar.click().catch(() => {});

    // Ou a transcrição aparece para confirmar, ou a tela avisa que não ouviu: nunca fica parada.
    const enviarAgora = page.getByRole("button", { name: "Enviar agora" });
    await expect.poll(async () => (await enviarAgora.isVisible()) || dialogos.some((m) => /Não consegui ouvir/.test(m)))
        .toBe(true);

    if (await enviarAgora.isVisible()) {
        await enviarAgora.click();
        const log = page.getByRole("log", { name: "Transcrição da entrevista" });
        await expect(log).toContainText("Resposta simulada em modo offline."); // texto do STT falso
        await expect(page.getByRole("button", { name: "Falar ao microfone" })).toBeEnabled(); // próxima fala chegou: vez da pessoa
    }
    expect(dialogos.filter((m) => !/Não consegui ouvir/.test(m))).toEqual([]);
    expect(erros).toEqual([]);
});

test("voz: microfone negado mostra o aviso e deixa passar para o modo escrever", async ({ page, request }) => {
    const erros = vigiarConsole(page);
    await page.addInitScript(() => {
        navigator.mediaDevices.getUserMedia = () =>
            Promise.reject(new DOMException("Permission denied", "NotAllowedError"));
    });

    const roteiro = await criarRoteiro(request, tituloUnico("Roteiro mic negado (E2E)"), ["Como é o seu dia a dia?"]);
    await page.goto(roteiro.link_convite);
    await page.getByRole("button", { name: "Falar" }).click();
    await page.getByRole("button", { name: "Começar" }).click();

    await page.getByRole("button", { name: "Falar ao microfone" }).click();
    await expect(page.getByRole("alert")).toContainText("Não consegui acessar o microfone");
    await expect(page.getByText("OUVINDO SUA RESPOSTA…")).toHaveCount(0);

    await page.getByRole("button", { name: /Prefiro escrever/ }).click();
    await expect(page.getByLabel("Sua resposta")).toBeEnabled();
    expect(erros).toEqual([]);
});
