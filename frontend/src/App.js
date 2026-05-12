import "@/App.css";
import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Landing from "@/pages/Landing";
import NotFound from "@/pages/NotFound";

// Админка тяжёлая и не нужна публичному посетителю — отдаём отдельным
// чанком, чтобы лендинг не платил за её bundle (~30-40 KB gzip).
const AdminLeads = lazy(() => import("@/pages/AdminLeads"));
const AdminLandingEdit = lazy(() => import("@/pages/AdminLandingEdit"));

function App() {
  return (
    <div className="App bg-cream">
      <BrowserRouter>
        <Toaster
          position="top-center"
          toastOptions={{
            style: {
              background: "#1B4D3E",
              color: "#fff",
              border: "1px solid rgba(255,255,255,.12)",
              fontFamily: "'DM Sans', system-ui, sans-serif",
            },
          }}
        />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route
            path="/admin/leads"
            element={
              <Suspense fallback={<AdminFallback />}>
                <AdminLeads />
              </Suspense>
            }
          />
          <Route
            path="/admin"
            element={
              <Suspense fallback={<AdminFallback />}>
                <AdminLeads />
              </Suspense>
            }
          />
          <Route
            path="/admin/landing-edit"
            element={
              <Suspense fallback={<AdminFallback />}>
                <AdminLandingEdit />
              </Suspense>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

function AdminFallback() {
  return (
    <div
      data-testid="admin-fallback"
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "var(--stone)",
        fontFamily: "var(--fb)",
        fontSize: 14,
      }}
    >
      Загрузка админки…
    </div>
  );
}

export default App;
