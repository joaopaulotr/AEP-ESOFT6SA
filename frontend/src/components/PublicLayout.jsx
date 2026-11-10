import React from "react";
import ThemeToggle from "./ThemeToggle";
import { CSS as UI_CSS } from "../styles/ui";

/** Layout das telas públicas (participante): sem menu lateral nem links do pesquisador. */
export default function PublicLayout({ children }) {
    return (
        <div style={s.root}>
            <style>{UI_CSS}</style>
            <div style={s.bar}><ThemeToggle /></div>
            <main style={s.main}>{children}</main>
        </div>
    );
}

const s = {
    root: { minHeight: "100vh", backgroundColor: "var(--color-bg)", fontFamily: "var(--font-sans)", color: "var(--color-text)", boxSizing: "border-box", padding: "12px 16px 32px" },
    bar: { display: "flex", justifyContent: "flex-end", maxWidth: 980, margin: "0 auto" },
    main: { maxWidth: 980, margin: "0 auto" },
};
