/**
 * Sessão da entrevista pública guardada no `sessionStorage` por slug (o id não vai na URL, para
 * não vazar em histórico, prints ou links compartilhados). Some ao fechar a aba.
 */
const chave = (slug) => `entrevista:${slug}`;

export function lerSessaoPublica(slug) {
    try {
        const bruto = sessionStorage.getItem(chave(slug));
        const dados = bruto ? JSON.parse(bruto) : null;
        return dados?.sessionId ? dados : null;
    } catch {
        return null;
    }
}

export function guardarSessaoPublica(slug, dados) {
    try {
        sessionStorage.setItem(chave(slug), JSON.stringify(dados));
    } catch {
        // sem storage: a entrevista segue enquanto a página estiver aberta
    }
}

/** Atualiza só o canal (voz/texto) da sessão guardada. */
export function guardarCanalPublico(slug, canal) {
    const atual = lerSessaoPublica(slug);
    if (atual) guardarSessaoPublica(slug, { ...atual, canal });
}
