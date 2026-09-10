import { useState } from "react";
import React from "react";
import LoginScreen from "./screens/LoginScreen";
import WelcomeScreen from "./screens/WelcomeScreen";
import InterviewScreen from "./screens/InterviewScreen";
import FeedbackScreen from "./screens/FeedbackScreen";
import { BrowserRouter, Routes, Route } from "react-router-dom";


export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<LoginScreen />} />
                <Route path="/welcome" element={<WelcomeScreen />} />
                <Route path="/entrevista" element={<InterviewScreen />} />
                <Route path="/feedback" element={<FeedbackScreen />} />
            </Routes>
        </BrowserRouter>
    );
}