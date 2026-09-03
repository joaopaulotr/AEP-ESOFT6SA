import { useState } from "react";
import React from "react";

export default function NavBar() {
    return (
        <div style={navBarStyle}></div>
    );
}

const navBarStyle = {
    width: "100%",
    height: 60,
    backgroundColor: "#ffffff",
    boxShadow: "0px 4px 12px rgba(0, 0, 0, 0.1)",
    display: "flex",
};