import { test, expect } from "@playwright/test";
import { tituloUnico, criarRoteiro, vigiarConsole, coletarDialogos } from "./helpers";

// Microfone falso do Chromium + STT/TTS falsos do backend: o ciclo inteiro da tela tem de acontecer
// (gravar → parar → confirmar a transcrição → próxima fala no log), sem atalhos condicionais.
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

    // Ciclo completo e obrigatório: o mic falso produz áudio e o STT falso devolve texto fixo.
    await page.getByRole("button", { name: "Parar e enviar resposta" }).click();

    const confirmar = page.getByRole("group", { name: "Confirmar o que foi entendido" });
    await expect(confirmar).toContainText("Resposta simulada em modo offline."); // texto do STT falso
    await expect(page.getByText(/Não consegui ouvir/)).toHaveCount(0);
    await confirmar.getByRole("button", { name: "Enviar agora" }).click();

    // A resposta entra na transcrição e, depois dela, a próxima fala da entrevistadora ("du · hh:mm").
    const log = page.getByRole("log", { name: "Transcrição da entrevista" });
    await expect(log).toContainText(/Resposta simulada em modo offline\.\s*du\s*·/);
    await expect(page.getByRole("button", { name: "Falar ao microfone" })).toBeEnabled(); // vez da pessoa de novo
    await expect(page.getByRole("alert")).toHaveCount(0);
    expect(dialogos).toEqual([]);
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
