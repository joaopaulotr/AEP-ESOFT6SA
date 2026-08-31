import { useState } from "react";
import React from "react";
import WelcomeScreen from "./screens/WelcomeScreen";


export default function App() {
  const [screen, setScreen] = useState("welcome"); // "welcome" | "interview"

  return (
    <>
      {screen === "welcome" && (
        <WelcomeScreen onStart={() => setScreen("interview")} />
      )}
      
    </>
  );
}