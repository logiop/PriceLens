import { useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppProvider } from "./lib/hooks";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Products } from "./pages/Products";
import { ProductDetail } from "./pages/ProductDetail";
import { Repricing } from "./pages/Repricing";
import { Competitors } from "./pages/Competitors";
import { Alerts } from "./pages/Alerts";
import { Audit } from "./pages/Audit";
import { clearTeamId, clearToken, isAuthed } from "./lib/auth";

export default function App() {
  const [authed, setAuthed] = useState(isAuthed());

  useEffect(() => {
    const onUnauthorized = () => setAuthed(false);
    window.addEventListener("pricelens:unauthorized", onUnauthorized);
    return () => window.removeEventListener("pricelens:unauthorized", onUnauthorized);
  }, []);

  return (
    <BrowserRouter>
      <AppProvider>
        {authed ? (
          <Routes>
            <Route
              element={
                <Layout
                  onLogout={() => {
                    clearToken();
                    clearTeamId();
                    setAuthed(false);
                  }}
                />
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="products" element={<Products />} />
              <Route path="products/:id" element={<ProductDetail />} />
              <Route path="repricing" element={<Repricing />} />
              <Route path="competitors" element={<Competitors />} />
              <Route path="alerts" element={<Alerts />} />
              <Route path="audit" element={<Audit />} />
            </Route>
          </Routes>
        ) : (
          <Login onAuth={() => setAuthed(true)} />
        )}
      </AppProvider>
    </BrowserRouter>
  );
}
