import { Navigate, Route, Routes } from "react-router-dom";

import { SplitPage } from "./pages/split-page";
import { RevealPage } from "./pages/reveal-page";
import { OperationsPage } from "./pages/operations-page";
import { SettingsPage } from "./pages/settings-page";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/split" replace />} />
      <Route path="/split" element={<SplitPage />} />
      <Route path="/reveal" element={<RevealPage />} />
      <Route path="/operations" element={<OperationsPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="*" element={<Navigate to="/split" replace />} />
    </Routes>
  );
}