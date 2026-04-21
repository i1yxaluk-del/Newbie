import { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Link } from "react-router-dom";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_LABELS = {
  new: "Новая",
  contacted: "Связались",
  qualified: "Квалифицирован",
  won: "Закрыта · Win",
  lost: "Закрыта · Lost",
};

export default function AdminLeads() {
  const [token, setToken] = useState(() => sessionStorage.getItem("msp_admin_token") || "");
  const [authed, setAuthed] = useState(false);
  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async (tkn) => {
    setLoading(true);
    try {
      const headers = { "X-Admin-Token": tkn };
      const [lr, sr] = await Promise.all([
        axios.get(`${API}/leads`, { headers }),
        axios.get(`${API}/stats`, { headers }),
      ]);
      setLeads(lr.data);
      setStats(sr.data);
      setAuthed(true);
      sessionStorage.setItem("msp_admin_token", tkn);
    } catch (err) {
      toast.error(err?.response?.status === 401 ? "Неверный токен" : "Ошибка загрузки");
      setAuthed(false);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) load(token);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const updateStatus = async (id, newStatus) => {
    try {
      await axios.patch(
        `${API}/leads/${id}/status?new_status=${newStatus}`,
        {},
        { headers: { "X-Admin-Token": token } },
      );
      setLeads((prev) => prev.map((l) => (l.id === id ? { ...l, status: newStatus } : l)));
      toast.success("Статус обновлён");
    } catch {
      toast.error("Не удалось обновить статус");
    }
  };

  if (!authed) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
        }}
      >
        <div
          data-testid="admin-login"
          style={{
            background: "#fff",
            border: "1px solid var(--rule)",
            borderRadius: 8,
            padding: 36,
            width: "100%",
            maxWidth: 420,
          }}
        >
          <div className="font-display" style={{ fontSize: 26, fontWeight: 500, marginBottom: 6 }}>
            MSP<span style={{ color: "var(--forest)" }}>Shield</span> · Admin
          </div>
          <p style={{ fontSize: 14, color: "var(--stone)", marginBottom: 22 }}>
            Введите токен администратора (ADMIN_TOKEN из backend/.env).
          </p>
          <input
            data-testid="admin-token-input"
            className="mspinput"
            type="password"
            placeholder="ADMIN_TOKEN"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load(token)}
          />
          <button
            data-testid="admin-login-btn"
            className="btn-core btn-primary"
            style={{ width: "100%", padding: 13, marginTop: 14 }}
            onClick={() => load(token)}
            disabled={loading || !token}
          >
            {loading ? "Загрузка…" : "Войти"}
          </button>
          <div style={{ marginTop: 20, textAlign: "center" }}>
            <Link to="/" style={{ fontSize: 13, color: "var(--stone)" }}>
              ← На сайт
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: "40px 0", minHeight: "100vh" }}>
      <div className="wrap">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            marginBottom: 30,
          }}
        >
          <div>
            <h1 className="font-display" style={{ fontSize: 36, fontWeight: 500 }}>
              Заявки
            </h1>
            <p style={{ fontSize: 14, color: "var(--stone)", marginTop: 4 }}>
              {stats ? (
                <>
                  Всего: <b>{stats.total_leads}</b> · сегодня: <b>{stats.leads_today}</b>
                </>
              ) : (
                "…"
              )}
            </p>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button
              className="btn-core btn-ghost"
              onClick={() => load(token)}
              data-testid="admin-refresh"
            >
              Обновить
            </button>
            <button
              className="btn-core btn-ghost"
              onClick={() => {
                sessionStorage.removeItem("msp_admin_token");
                setToken("");
                setAuthed(false);
              }}
              data-testid="admin-logout"
            >
              Выйти
            </button>
          </div>
        </div>

        <div
          style={{
            background: "#fff",
            border: "1px solid var(--rule)",
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
          <div style={{ overflowX: "auto" }}>
            <table
              data-testid="admin-leads-table"
              style={{ width: "100%", borderCollapse: "collapse", fontSize: 13.5, minWidth: 960 }}
            >
              <thead>
                <tr>
                  {["Дата", "Компания · Имя", "Контакт", "Серверы", "Тариф", "Сообщение", "Статус"].map(
                    (h) => (
                      <th key={h} style={adminTh}>
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {leads.map((l) => (
                  <tr key={l.id} data-testid={`lead-row-${l.id}`}>
                    <td style={{ ...adminTd, whiteSpace: "nowrap", fontFamily: "var(--fm)", fontSize: 11.5 }}>
                      {new Date(l.created_at).toLocaleString("ru-RU")}
                    </td>
                    <td style={adminTd}>
                      <b>{l.company}</b>
                      <div style={{ color: "var(--stone)", fontSize: 12 }}>{l.name}</div>
                    </td>
                    <td style={adminTd}>
                      {l.contact}
                      {l.email && (
                        <div style={{ color: "var(--stone)", fontSize: 12 }}>{l.email}</div>
                      )}
                    </td>
                    <td style={adminTd}>{l.servers}</td>
                    <td style={adminTd}>
                      <span
                        className="font-mono"
                        style={{
                          fontSize: 11,
                          color: "var(--forest)",
                          background: "var(--forest-dim)",
                          border: "1px solid var(--forest-bdr)",
                          padding: "3px 8px",
                          borderRadius: 3,
                        }}
                      >
                        {l.tariff}
                      </span>
                    </td>
                    <td style={{ ...adminTd, maxWidth: 280, color: "var(--stone)" }}>
                      {l.message || "—"}
                    </td>
                    <td style={adminTd}>
                      <select
                        className="mspinput"
                        style={{ padding: "6px 10px", fontSize: 12.5 }}
                        value={l.status}
                        onChange={(e) => updateStatus(l.id, e.target.value)}
                        data-testid={`lead-status-${l.id}`}
                      >
                        {Object.entries(STATUS_LABELS).map(([k, v]) => (
                          <option key={k} value={k}>
                            {v}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {leads.length === 0 && (
            <div style={{ textAlign: "center", padding: 48, color: "var(--stone)" }}>
              Заявок пока нет
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const adminTh = {
  padding: "14px 16px",
  textAlign: "left",
  fontWeight: 500,
  fontSize: 12,
  letterSpacing: ".04em",
  textTransform: "uppercase",
  color: "var(--stone)",
  borderBottom: "1px solid var(--rule)",
};
const adminTd = {
  padding: "14px 16px",
  borderBottom: "1px solid var(--rule-lt)",
  color: "var(--ink-2)",
  verticalAlign: "top",
};
