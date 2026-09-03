import { useState } from "react";
import React from "react";

export default function Pointer({ size = 14, cor = "rgb(226, 90, 0)", style: extraStyle }) {
    return (
        <>
            <style>{`
                @keyframes radar {
                    0%   { transform: translate(-50%, -50%) scale(1); opacity: 0.6; }
                    100% { transform: translate(-50%, -50%) scale(2); opacity: 0; }
                }
            `}</style>

            <div
                style={{
                    position: "relative",
                    width: size,
                    height: size,
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    ...extraStyle,
                }}
            >
               
                <div style={radarStyle(size, cor)} />

              
              
            </div>
        </>
    );
}

function radarStyle(size, cor) {
    return {
        position: "absolute",
        top: "50%",
        left: "50%",
        width: size,
        height: size,
        borderRadius: "50%",
        backgroundColor: cor,
        animation: "radar 1s ease-out infinite",
    };
}