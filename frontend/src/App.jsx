import { useState } from "react";
import React from "react";
import WelcomeScreen from "./screens/WelcomeScreen";
import InterviewScreen from "./screens/InterviewScreen";
import { BrowserRouter, Routes, Route } from "react-router-dom";


export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<WelcomeScreen />} />
                <Route path="/entrevista" element={<InterviewScreen />} />
            </Routes>
        </BrowserRouter>
    );
}