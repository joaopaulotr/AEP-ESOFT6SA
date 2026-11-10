/**
 * Modo E2E (Playwright): com VITE_E2E=1 os atrasos de realismo (tempo de "pensar", digitação
 * letra a letra, fillers de voz e o incentivo por silêncio) ficam desligados, para os testes
 * esperarem pelo estado da tela e não por tempo. Em produção a variável não existe: E2E = false.
 */
export const E2E = import.meta.env.VITE_E2E === "1";
