import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Link } from "react-router-dom";

// Same-origin fallback (prod nginx). В CRA dev REACT_APP_BACKEND_URL берётся из .env.
const BACKEND = (process.env.REACT_APP_BACKEND_URL || "").replace(/\/$/, "");
const API = `${BACKEND}/api`;

const STORAGE_TOKEN = "msp_admin_jwt";
const STORAGE_LEGACY = "msp_admin_token"; // back-compat

const STATUS_LABELS = {
  new: "Новая",
  contacted: "Связались",
  qualified: "Квалифицирован",
  won: "Закрыта · Win",
  lost: "Закрыта · Lost",
};

const TARIFF_OPTIONS = ["bronze", "silver", "gold", "undecided"];

function authHeaders() {
  const jwt = localStorage.getItem(STORAGE_TOKEN);
  if (jwt) return { Authorization: `Bearer ${jwt}` };
  const legacy = sessionStorage.getItem(STORAGE_LEGACY);
  if (legacy) return { "X-Admin-Token": legacy };
  return {};
}

function clearAuth() {
  localStorage.removeItem(STORAGE_TOKEN);
  sessionStorage.removeItem(STORAGE_LEGACY);
}

export default function AdminLeads() {
  const [authed, setAuthed] = useState(false);
  const [password, setPassword] = useState("");
  const [loginPending, setLoginPending] = useState(false);
  const [diagnostic, setDiagnostic] = useState(null);
  const [healthOk, setHealthOk] = useState(null);

  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({ status: "", tariff: "" });

  // Pre-flight: всегда проверяем /api/health, чтобы отличить «backend down» от «401».
  useEffect(() => {
    let cancelled = false;
    axios
      .get(`${API}/health`, { timeout: 8000 })
      .then(() => !cancelled && setHealthOk(true))
      .catch(() => !cancelled && setHealthOk(false));
    return () => {
      cancelled = true;
    };
  }, []);

  // Если есть JWT в localStorage — пробуем авто-логин через /admin/whoami.
  useEffect(() => {
    const headers = authHeaders();
    if (!Object.keys(headers).length) return;
    axios
      .get(`${API}/admin/whoami`, { headers })
      .then(() => {
        setAuthed(true);
        loadLeads();
      })
      .catch((err) => {
        if (err?.response?.status === 401) clearAuth();
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadLeads = async () => {
    setLoading(true);
    setDiagnostic(null);
    try {
      const headers = authHeaders();
      const params = {};
      if (filters.status) params.status = filters.status;
      if (filters.tariff) params.tariff = filters.tariff;
      const [lr, sr] = await Promise.all([
        axios.get(`${API}/leads`, { headers, params }),
        axios.get(`${API}/stats`, { headers }),
      ]);
      setLeads(lr.data);
      setStats(sr.data);
      setAuthed(true);
    } catch (err) {
      handleApiError(err);
      if (err?.response?.status === 401) {
        clearAuth();
        setAuthed(false);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleApiError = (err) => {
    const status = err?.response?.status;
    const detail = err?.response?.data?.detail;
    if (status === 401) {
      setDiagnostic("401: пароль не совпадает с ADMIN_TOKEN на сервере или JWT истёк.");
    } else if (status === 503 || detail === "Admin access not configured") {
      setDiagnostic(
        "503: на сервере пустой ADMIN_TOKEN. В backend/.env задай ADMIN_TOKEN=$(openssl rand -hex 32) и перезапусти backend.",
      );
    } else if (!status) {
      setDiagnostic(
        `API недоступен: ${API || "(same-origin)"}. Проверь REACT_APP_BACKEND_URL или nginx-проксирование /api/.`,
      );
    } else {
      setDiagnostic(`HTTP ${status}${detail ? `: ${detail}` : ""}`);
    }
  };

  const onLogin = async (e) => {
    e.preventDefault();
    if (!password) return;
    setLoginPending(true);
    setDiagnostic(null);
    try {
      const r = await axios.post(`${API}/admin/login`, { password });
      localStorage.setItem(STORAGE_TOKEN, r.data.token);
      sessionStorage.removeItem(STORAGE_LEGACY);
      toast.success("Вход выполнен");
      setPassword("");
      setAuthed(true);
      await loadLeads();
    } catch (err) {
      handleApiError(err);
      if (err?.response?.status === 401) toast.error("Неверный пароль");
      else toast.error("Не удалось войти");
    } finally {
      setLoginPending(false);
    }
  };

  const updateStatus = async (id, newStatus) => {
    try {
      await axios.patch(`${API}/leads/${id}/status?new_status=${newStatus}`, {}, {
        headers: authHeaders(),
      });
      setLeads((prev) => prev.map((l) => (l.id === id ? { ...l, status: newStatus } : l)));
      toast.success("Статус обновлён");
    } catch (err) {
      handleApiError(err);
      toast.error("Не удалось обновить статус");
    }
  };

  const onLogout = () => {
    clearAuth();
    setAuthed(false);
    setLeads([]);
    setStats(null);
    toast.success("Вы вышли");
  };

  const onExportCsv = () => {
    const headers = authHeaders();
    const url = `${API}/leads.csv`;
    fetch(url, { headers })
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.blob();
      })
      .then((blob) => {
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = `mspshield-leads-${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(link);
        link.click();
        link.remove();
      })
      .catch((err) => {
        toast.error("Не удалось скачать CSV");
        handleApiError({ response: { status: err?.message?.match(/\d+/)?.[0] } });
      });
  };

  const filteredApply = () => loadLeads();

  const visibleLeads = useMemo(() => leads, [leads]);

  if (!authed) {
    return (
      <LoginScreen
        password={password}
        setPassword={setPassword}
        onSubmit={onLogin}
        pending={loginPending}
        diagnostic={diagnostic}
        healthOk={healthOk}
      />
    );
  }

  return (
    <div style={{ padding: "32px 0", minHeight: "100vh" }}>
      <div className="wrap">
        <Header
          stats={stats}
          onRefresh={loadLeads}
          onLogout={onLogout}
          onExportCsv={onExportCsv}
          loading={loading}
        />

        {diagnostic && <Diagnostic text={diagnostic} />}

        <Filters filters={filters} setFilters={setFilters} onApply={filteredApply} />

        <div
          style={{
            background: "#fff",
            border: "1px solid var(--rule)",
            borderRadius: 6,
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
                  {[
                    "Дата",
                    "Компания · Имя",
                    "Контакт",
                    "Серверы",
                    "Тариф",
                    "Источник",
                    "Сообщение",
                    "Kaiten",
                    "Статус",
                  ].map((h) => (
                    <th key={h} style={adminTh}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleLeads.map((l) => (
                  <LeadRow key={l.id} l={l} updateStatus={updateStatus} />
                ))}
              </tbody>
            </table>
          </div>
          {visibleLeads.length === 0 && (
            <div style={{ textAlign: "center", padding: 48, color: "var(--stone)" }}>
              Заявок пока нет
            </div>
          )}
        </div>

        <p style={{ fontSize: 12, color: "var(--stone-lt)", marginTop: 24, textAlign: "center" }}>
          MSPShield Admin · JWT-сессия (24 ч) · X-Admin-Token остаётся для CLI/curl.
        </p>
      </div>
    </div>
  );
}

function LoginScreen({ password, setPassword, onSubmit, pending, diagnostic, healthOk }) {
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
      <form
        onSubmit={onSubmit}
        data-testid="admin-login"
        style={{
          background: "#fff",
          border: "1px solid var(--rule)",
          borderRadius: 6,
          padding: 32,
          width: "100%",
          maxWidth: 380,
        }}
      >
        <div style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>
          MSPShield · Admin
        </div>
        <p style={{ fontSize: 13, color: "var(--stone)", marginBottom: 18, lineHeight: 1.6 }}>
          Введите пароль администратора (значение `ADMIN_TOKEN` из backend/.env).
        </p>

        {healthOk === false && (
          <div data-testid="admin-health-warn" style={diagnosticStyle}>
            Backend недоступен ({API || "/api"}). Проверь, что сервис запущен и
            что `REACT_APP_BACKEND_URL` или nginx настроены корректно.
          </div>
        )}
        {diagnostic && <div data-testid="admin-diagnostic" style={diagnosticStyle}>{diagnostic}</div>}

        <input
          data-testid="admin-token-input"
          className="mspinput"
          type="password"
          placeholder="ADMIN_TOKEN"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
        />
        <button
          data-testid="admin-login-btn"
          type="submit"
          className="btn-core btn-primary"
          style={{ width: "100%", padding: 12, marginTop: 14 }}
          disabled={pending || !password || healthOk === false}
        >
          {pending ? "Проверка…" : "Войти"}
        </button>

        <div style={{ marginTop: 18, textAlign: "center" }}>
          <Link to="/" style={{ fontSize: 13, color: "var(--stone)" }}>
            ← На сайт
          </Link>
        </div>
      </form>
    </div>
  );
}

function Header({ stats, onRefresh, onLogout, onExportCsv, loading }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "baseline",
        marginBottom: 24,
        flexWrap: "wrap",
        gap: 16,
      }}
    >
      <div>
        <h1 style={{ fontSize: 28, fontWeight: 600, margin: 0 }}>Заявки</h1>
        <p style={{ fontSize: 13, color: "var(--stone)", marginTop: 4 }}>
          {stats ? (
            <>
              Всего: <b>{stats.total_leads}</b> · сегодня: <b>{stats.leads_today}</b>
              {stats.by_status?.new ? <> · новых: <b>{stats.by_status.new}</b></> : null}
            </>
          ) : (
            "…"
          )}
        </p>
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button className="btn-core btn-ghost" onClick={onRefresh} data-testid="admin-refresh" disabled={loading}>
          {loading ? "Загрузка…" : "Обновить"}
        </button>
        <button className="btn-core btn-ghost" onClick={onExportCsv} data-testid="admin-export-csv">
          Экспорт CSV
        </button>
        <button className="btn-core btn-ghost" onClick={onLogout} data-testid="admin-logout">
          Выйти
        </button>
      </div>
    </div>
  );
}

function Filters({ filters, setFilters, onApply }) {
  return (
    <div
      data-testid="admin-filters"
      style={{
        display: "flex",
        gap: 8,
        marginBottom: 16,
        flexWrap: "wrap",
        alignItems: "center",
      }}
    >
      <select
        className="mspinput"
        value={filters.status}
        onChange={(e) => setFilters({ ...filters, status: e.target.value })}
        style={{ width: 200 }}
        data-testid="filter-status"
      >
        <option value="">Все статусы</option>
        {Object.entries(STATUS_LABELS).map(([k, v]) => (
          <option key={k} value={k}>
            {v}
          </option>
        ))}
      </select>
      <select
        className="mspinput"
        value={filters.tariff}
        onChange={(e) => setFilters({ ...filters, tariff: e.target.value })}
        style={{ width: 180 }}
        data-testid="filter-tariff"
      >
        <option value="">Все тарифы</option>
        {TARIFF_OPTIONS.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>
      <button className="btn-core btn-ghost" onClick={onApply} data-testid="filter-apply">
        Применить
      </button>
    </div>
  );
}

function LeadRow({ l, updateStatus }) {
  return (
    <tr data-testid={`lead-row-${l.id}`}>
      <td style={{ ...adminTd, whiteSpace: "nowrap", fontFamily: "var(--fm)", fontSize: 11.5 }}>
        {new Date(l.created_at).toLocaleString("ru-RU")}
      </td>
      <td style={adminTd}>
        <b>{l.company}</b>
        <div style={{ color: "var(--stone)", fontSize: 12 }}>{l.name}</div>
      </td>
      <td style={adminTd}>
        {l.contact}
        {l.email && <div style={{ color: "var(--stone)", fontSize: 12 }}>{l.email}</div>}
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
      <td style={{ ...adminTd, fontSize: 12, color: "var(--stone)" }}>
        {l.source || "landing"}
      </td>
      <td style={{ ...adminTd, color: "var(--stone)", fontSize: 12.5 }}>
        <div
          title={l.message || ""}
          style={{
            maxWidth: 260,
            display: "-webkit-box",
            WebkitLineClamp: 3,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
            wordBreak: "break-word",
            overflowWrap: "anywhere",
            lineHeight: 1.4,
          }}
        >
          {l.message || "—"}
        </div>
      </td>
      <td style={adminTd}>
        {l.kaiten_card_url ? (
          <a
            href={l.kaiten_card_url}
            target="_blank"
            rel="noreferrer"
            style={{ fontSize: 12, color: "var(--forest)" }}
            data-testid={`kaiten-link-${l.id}`}
          >
            Открыть ↗
          </a>
        ) : l.kaiten_card_id ? (
          <span style={{ fontSize: 11, color: "var(--stone-lt)" }}>#{l.kaiten_card_id}</span>
        ) : (
          <span style={{ fontSize: 11, color: "var(--stone-lt)" }}>—</span>
        )}
      </td>
      <td style={adminTd}>
        <select
          className="mspinput"
          style={{ padding: "6px 10px", fontSize: 12.5, minWidth: 140 }}
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
  );
}

function Diagnostic({ text }) {
  return <div style={diagnosticStyle}>{text}</div>;
}

const diagnosticStyle = {
  background: "#fff5f0",
  border: "1px solid #f0cdbc",
  borderRadius: 4,
  padding: "10px 12px",
  fontSize: 12.5,
  color: "#8a4a2a",
  marginBottom: 14,
  lineHeight: 1.5,
};

const adminTh = {
  textAlign: "left",
  fontWeight: 500,
  fontSize: 11.5,
  letterSpacing: ".06em",
  textTransform: "uppercase",
  color: "var(--stone)",
  borderBottom: "1px solid var(--rule)",
  padding: "12px 14px",
  background: "var(--cream)",
};
const adminTd = {
  padding: "12px 14px",
  borderTop: "1px solid var(--rule-lt)",
  verticalAlign: "top",
};
