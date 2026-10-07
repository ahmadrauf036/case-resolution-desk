import { BrowserRouter, Route, Routes } from "react-router-dom";
import { HealthProvider } from "./health";
import { CasesProvider } from "./cases";
import { AppShell } from "./components/AppShell";
import Home from "./pages/Home";
import CaseDetail from "./pages/CaseDetail";
import Preview from "./pages/Preview";

export default function App() {
  return (
    <HealthProvider>
      <CasesProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AppShell />}>
              <Route path="/" element={<Home />} />
              <Route path="/cases/:id" element={<CaseDetail />} />
              <Route path="/preview" element={<Preview />} />
              <Route path="*" element={<Home />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </CasesProvider>
    </HealthProvider>
  );
}