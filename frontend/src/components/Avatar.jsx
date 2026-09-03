import { useState } from "react";
import React from "react";

export default function Avatar({ size = 64, style: extraStyle }) {
    return (
        <>
            <style>{`
                @keyframes onda {
                    0% {
                        transform: translate(-50%, -50%) scale(1);
                        opacity: 0.6;
                    }
                    100% {
                        transform: translate(-50%, -50%) scale(2);
                        opacity: 0;
                    }
                }
                    @keyframes pulsar {
                    0%, 100% { transform: scale(1); }
                    50%      { transform: scale(1.1); }
                }
                    
            `}</style>
            <div
                style={{
                    position: "relative",
                    width: size,
                    height: size,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    ...extraStyle,
                }}
            >
               
                <div style={ondaStyle(size, "0s")} />
                <div style={ondaStyle(size, "1s")} />
                <div style={ondaStyle(size, "3s")} />

             
                <div
                    style={{
                        position: "relative",
                        width: size,
                        height: size,
                        animation: "pulsar 4s ease-in-out infinite",
                        borderRadius: "50%",
                        boxShadow: "0px 12px 24px rgba(127, 168, 159, 0.25)", 
                        background: `
                            radial-gradient(circle at left center, #bcddf3, transparent 50%),
                            radial-gradient(circle at center, #ffffff, transparent 50%),
                            
                            radial-gradient(circle at center bottom, #a0c9ca, transparent 55%),
                            #f1faff
                        `,
                    }}
                />
            </div>
        </>
    );
}


function ondaStyle(size, delay) {
    return {
        position: "absolute",
        top: "50%",
        left: "50%",
        width: size,
        height: size,
        borderRadius: "50%",
        border: "1px solid #98d3c67e",
        animation: "onda 7s ease-out infinite",
        animationDelay: delay,
    };
}