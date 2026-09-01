import { useState } from "react";
import React from "react";
import WelcomeScreen from "./screens/WelcomeScreen";
import InterviewScreen from "./screens/InterviewScreen";


export default function App() {
  const [screen, setScreen] = useState("welcome"); // "welcome" | "interview"

  return (
    <>
      {screen === "welcome" && (
        <WelcomeScreen onStart={() => setScreen("interview")} />
      )}
      {screen === "interview" && <InterviewScreen />}
    </>
  );
}