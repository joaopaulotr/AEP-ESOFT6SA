import { useState } from "react";
import React from "react";

export default function Layout({ children }) {
      return <div style={root}>{children}</div>;
}

const root ={
    
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: 24,
        backgroundColor: "#e4f3f0",
    
};