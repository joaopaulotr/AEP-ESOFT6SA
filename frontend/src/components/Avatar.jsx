import { useState } from "react";
import React from "react";

export default function Avatar() {
    return <div style={avatarStyle} />;
}

const avatarStyle = {
    width: 64,
    height: 64,
    borderRadius: 32,
    background: `
        radial-gradient(circle at left center, #e2aed1, transparent 50%),
        radial-gradient(circle at right center, #b6cf99, transparent 50%),
        radial-gradient(circle at center bottom, #ff743d, transparent 55%),
        #f1faff
    `,
};