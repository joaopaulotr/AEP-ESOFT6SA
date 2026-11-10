import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Carrega um recurso da API: { data, carregando, erro, recarregar }.
 * `recarregar()` mantém o dado atual até a nova resposta; mudar `deps` limpa o dado.
 * `carregar` deve ser estável por `deps`; refaz a busca quando as deps mudam.
 */
export function useApiResource(carregar, deps = []) {
    const [data, setData] = useState(null);
    const [carregando, setCarregando] = useState(true);
    const [erro, setErro] = useState("");
    const versaoRef = useRef(0);

    const carregarDados = useCallback(async (limpar) => {
        const versao = ++versaoRef.current;
        if (limpar) setData(null); // só quando a chave muda; recarregar mantém o que já está na tela
        setCarregando(true);
        setErro("");
        try {
            const resultado = await carregar();
            if (versao === versaoRef.current) setData(resultado);
        } catch (e) {
            if (versao === versaoRef.current) {
                setErro(e.detail || "Não consegui carregar. O servidor está no ar?");
            }
        } finally {
            if (versao === versaoRef.current) setCarregando(false);
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, deps);

    useEffect(() => {
        carregarDados(true);
        return () => { versaoRef.current++; };
    }, [carregarDados]);

    const recarregar = useCallback(() => carregarDados(false), [carregarDados]);

    return { data, carregando, erro, recarregar };
}
