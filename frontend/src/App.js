import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Landing from "@/pages/Landing";
import AdminLeads from "@/pages/AdminLeads";
import NotFound from "@/pages/NotFound";

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
          <Route path="/admin/leads" element={<AdminLeads />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
