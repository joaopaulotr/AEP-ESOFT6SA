/**
 * Modo E2E (Playwright): com VITE_E2E=1 os atrasos de realismo (tempo de "pensar", digitação
 * letra a letra, fillers de voz e o incentivo por silêncio) ficam desligados, para os testes
 * esperarem pelo estado da tela e não por tempo. Só vale no servidor de desenvolvimento
 * (`import.meta.env.DEV`): num build de produção o atalho nunca liga, mesmo com a variável definida.
 */
export const E2E = import.meta.env.DEV && import.meta.env.VITE_E2E === "1";
