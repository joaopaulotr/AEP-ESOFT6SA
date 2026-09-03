import { useState } from "react";
import React from "react";
import NavBar from "./NavBar";

export default function Layout({ children }) {
        return (
        <div style={root}>
            
            <style>{FONTS}</style>
            {children}
        </div>
    );
      
}

const FONTS = `
@import url('https://fonts.googleapis.com/css2?family=Coiny&family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=Lexend:wght@700&family=Momo+Trust+Display&family=Momo+Trust+Sans:wght@200..800&family=Paytone+One&family=Silkscreen:wght@400;700&display=swap');`

const root ={
    
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: 24,
        backgroundColor: "#f1faf8",
        
};