import { useEffect, useState } from "react";


export function useElapsedTime() {
    const [segundos, setSegundos] = useState(0);

    useEffect(() => {
        const t = setInterval(() => setSegundos((s) => s + 1), 1000);
        return () => clearInterval(t);
    }, []);

    return segundos;
}
