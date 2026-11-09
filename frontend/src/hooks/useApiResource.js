import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Carrega um recurso da API: { data, carregando, erro, recarregar }.
 * `carregar` deve ser estável por `deps`; refaz a busca quando as deps mudam.
 */
export function useApiResource(carregar, deps = []) {
    const [data, setData] = useState(null);
    const [carregando, setCarregando] = useState(true);
    const [erro, setErro] = useState("");
    const versaoRef = useRef(0);

    const recarregar = useCallback(async () => {
        const versao = ++versaoRef.current;
        setData(null);
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
        recarregar();
        return () => { versaoRef.current++; };
    }, [recarregar]);

    return { data, carregando, erro, recarregar };
}
