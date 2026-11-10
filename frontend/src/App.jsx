
import LoginScreen from "./screens/LoginScreen";
import WelcomeScreen from "./screens/WelcomeScreen";
import InterviewScreen from "./screens/InterviewScreen";
import FeedbackScreen from "./screens/FeedbackScreen";
import ScriptsScreen from "./screens/ScriptsScreen";
import ScriptSessionsScreen from "./screens/ScriptSessionsScreen";
import ScriptDashboardScreen from "./screens/ScriptDashboardScreen";
import SessionDetailScreen from "./screens/SessionDetailScreen";
import ScriptEditorScreen from "./screens/ScriptEditorScreen";
import ScriptImportScreen from "./screens/ScriptImportScreen";
import InviteScreen from "./screens/InviteScreen";
import ThankYouScreen from "./screens/ThankYouScreen";
import { BrowserRouter, Routes, Route } from "react-router-dom";


export default function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<LoginScreen />} />
                <Route path="/welcome" element={<WelcomeScreen />} />
                <Route path="/entrevistas" element={<ScriptsScreen />} />
                <Route path="/roteiros/novo" element={<ScriptEditorScreen />} />
                <Route path="/roteiros/importar" element={<ScriptImportScreen />} />
                <Route path="/roteiros/:scriptId/editar" element={<ScriptEditorScreen />} />
                <Route path="/entrevistas/:scriptId" element={<ScriptSessionsScreen />} />
                <Route path="/entrevistas/:scriptId/painel" element={<ScriptDashboardScreen />} />
                <Route path="/sessao/:sessionId" element={<SessionDetailScreen />} />
                <Route path="/entrevista" element={<InterviewScreen />} />
                <Route path="/e/:slug" element={<InviteScreen />} />
                <Route path="/e/:slug/entrevista" element={<InterviewScreen publico />} />
                <Route path="/e/:slug/obrigado" element={<ThankYouScreen />} />
                <Route path="/feedback" element={<FeedbackScreen />} />
            </Routes>
        </BrowserRouter>
    );
}