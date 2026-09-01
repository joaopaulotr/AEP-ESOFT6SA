import { useState } from "react";
import React from "react";

export default function Avatar({ size = 64, style: extraStyle }) {
    return (
        <div
            style={{
                width: size,
                height: size,
                borderRadius: size / 2,  
                flexShrink: 0,
                background: `
                    radial-gradient(circle at left center, #e2aed1, transparent 50%),
                    radial-gradient(circle at right center, #b6cf99, transparent 50%),
                    radial-gradient(circle at center bottom, #ff743d, transparent 55%),
                    #f1faff
                `,
                ...extraStyle,  
            }}
        />
    );
}