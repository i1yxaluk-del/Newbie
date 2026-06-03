const SERVICES = {
  windows: { kind: "shape", render: () => (
    <>
      <rect x="2" y="2" width="9.5" height="9.5" rx="1" fill="currentColor" opacity=".9" />
      <rect x="12.5" y="2" width="9.5" height="9.5" rx="1" fill="currentColor" opacity=".9" />
      <rect x="2" y="12.5" width="9.5" height="9.5" rx="1" fill="currentColor" opacity=".9" />
      <rect x="12.5" y="12.5" width="9.5" height="9.5" rx="1" fill="currentColor" opacity=".9" />
    </>
  ) },
  ad: { kind: "shape", render: () => (
    <>
      <circle cx="12" cy="8" r="3.8" fill="none" stroke="currentColor" strokeWidth="1.8" />
      <path d="M4.5 22c0-4.2 3.4-7 7.5-7s7.5 2.8 7.5 7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="12" cy="12" r="10.5" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="2.5 2" opacity=".5" />
    </>
  ) },
  onec: { kind: "shape", render: () => (
    <>
      <rect x="2" y="2" width="20" height="20" rx="3" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <text x="12" y="12.5" dominantBaseline="central" textAnchor="middle" fontSize="9" fontFamily="system-ui,sans-serif" fontWeight="800" fill="currentColor">1С</text>
    </>
  ) },
  mssql: { kind: "shape", render: () => (
    <>
      <ellipse cx="12" cy="5.5" rx="9" ry="3.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M3 5.5v13c0 1.9 4 3.5 9 3.5s9-1.6 9-3.5v-13" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M3 12c0 1.9 4 3.5 9 3.5s9-1.6 9-3.5" fill="none" stroke="currentColor" strokeWidth="1.2" opacity=".5" />
    </>
  ) },
  mail: { kind: "shape", render: () => (
    <>
      <rect x="2" y="5" width="20" height="14" rx="2.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M2.5 7.5l9.5 6.5 9.5-6.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <circle cx="20" cy="5" r="3.5" fill="currentColor" opacity=".2" />
      <text x="20" y="5.5" dominantBaseline="central" textAnchor="middle" fontSize="4.5" fontFamily="system-ui,sans-serif" fontWeight="700" fill="currentColor">@</text>
    </>
  ) },
  fileserver: { kind: "shape", render: () => (
    <>
      <path d="M3 6a2 2 0 0 1 2-2h5.5l2 2H19a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M8 12h8M8 15h5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity=".5" />
    </>
  ) },
  web: { kind: "shape", render: () => (
    <>
      <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <ellipse cx="12" cy="12" rx="4.5" ry="10" fill="none" stroke="currentColor" strokeWidth="1.2" />
      <path d="M2.5 9h19M2.5 15h19" stroke="currentColor" strokeWidth="1" opacity=".5" />
    </>
  ) },
  database: { kind: "shape", render: () => (
    <>
      <ellipse cx="12" cy="5" rx="9" ry="3" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3" fill="none" stroke="currentColor" strokeWidth="1.2" opacity=".5" />
    </>
  ) },
  vpn: { kind: "shape", render: () => (
    <>
      <path d="M12 2C8.5 2 5 4.5 5 8.5V12H4a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1v-8a1 1 0 0 0-1-1h-1V8.5C19 4.5 15.5 2 12 2zm0 2c2.7 0 5 1.8 5 4.5V12H7V8.5C7 5.8 9.3 4 12 4z" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <circle cx="12" cy="17" r="2" fill="currentColor" />
    </>
  ) },
  "shield-lock": { kind: "shape", render: () => (
    <>
      <path d="M12 1.5L3 5v6.5c0 5.5 3.8 9.8 9 11.5 5.2-1.7 9-6 9-11.5V5L12 1.5z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M12 1.5v21" stroke="currentColor" strokeWidth=".8" opacity=".2" />
      <path d="M12 1.5L3 5v6.5c0 5.5 3.8 9.8 9 11.5" fill="currentColor" opacity=".06" />
      <rect x="8.5" y="11" width="7" height="5.5" rx="1.2" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M10.5 11V9.5a1.5 1.5 0 0 1 3 0V11" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="12" cy="14" r=".8" fill="currentColor" />
    </>
  ) },
  server: { kind: "shape", render: () => (
    <>
      <rect x="3" y="3" width="18" height="6" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <rect x="3" y="9.5" width="18" height="6" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <rect x="3" y="16" width="18" height="6" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="6" cy="6" r="1" fill="currentColor" />
      <circle cx="6" cy="12.5" r="1" fill="currentColor" />
      <circle cx="6" cy="19" r="1" fill="currentColor" />
      <path d="M10 6h8M10 12.5h8M10 19h8" stroke="currentColor" strokeWidth=".8" opacity=".3" />
    </>
  ) },
  virt: { kind: "shape", render: () => (
    <>
      <rect x="3" y="3" width="18" height="18" rx="2" fill="none" stroke="currentColor" strokeWidth="1.4" strokeDasharray="3 2" />
      <rect x="6" y="6" width="12" height="12" rx="1.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <text x="12" y="12.5" dominantBaseline="central" textAnchor="middle" fontSize="7" fontFamily="system-ui,sans-serif" fontWeight="800" fill="currentColor">VM</text>
    </>
  ) },
  iis: { kind: "shape", render: () => (
    <>
      <rect x="2" y="2" width="20" height="20" rx="3" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <text x="12" y="12.5" dominantBaseline="central" textAnchor="middle" fontSize="8" fontFamily="system-ui,sans-serif" fontWeight="800" fill="currentColor">IIS</text>
    </>
  ) },
  cloud: { kind: "shape", render: () => (
    <>
      <path d="M6.5 18h11a5 5 0 0 0 .5-9.97A7 7 0 0 0 5 11a5 5 0 0 0 1.5 7z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M8 18v2M12 18v2M16 18v2" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      <circle cx="8.5" cy="14" r=".8" fill="currentColor" />
      <circle cx="12" cy="13" r=".8" fill="currentColor" />
      <circle cx="15.5" cy="14" r=".8" fill="currentColor" />
    </>
  ) },
  telegram: { kind: "shape", render: () => (
    <>
      <path d="M22 3L2 10.5l5.5 2.5L19 7l-5.5 7 1.5 5.5 3-3.5 4 3z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
    </>
  ) },
  max: { kind: "shape", render: () => (
    <>
      <rect x="2" y="2" width="20" height="20" rx="6" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <text x="12" y="12.5" dominantBaseline="central" textAnchor="middle" fontSize="11" fontFamily="system-ui,sans-serif" fontWeight="700" fill="currentColor">M</text>
    </>
  ) },
  more: { kind: "shape", render: () => (
    <>
      <rect x="2" y="2" width="20" height="20" rx="5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeDasharray="2.5 3" />
      <circle cx="7.5" cy="12" r="1.5" fill="currentColor" />
      <circle cx="12" cy="12" r="1.5" fill="currentColor" />
      <circle cx="16.5" cy="12" r="1.5" fill="currentColor" />
    </>
  ) },
};

export default function ServiceIcon({ name, size = 24, color = "currentColor", style }) {
  const m = SERVICES[name];
  if (!m) return null;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      role="img"
      aria-label={name}
      style={{ color, ...style }}
    >
      {m.render()}
    </svg>
  );
}

export const SERVICE_LIST = [
  { name: "web", label: "Веб-сайт", desc: "95% клиентов · Nginx / IIS, TLS, мониторинг" },
  { name: "onec", label: "1С:Предприятие", desc: "70% клиентов · сервер + БД, бэкапы 30д" },
  { name: "ad", label: "Active Directory", desc: "55% клиентов · DC, GPO, репликация" },
  { name: "mail", label: "Почта + DNS", desc: "90% клиентов · iRedMail, MX, SPF/DKIM" },
  { name: "fileserver", label: "Файловый сервер", desc: "80% клиентов · Samba / Windows shares" },
  { name: "database", label: "База данных", desc: "60% клиентов · PostgreSQL, MS SQL" },
  { name: "windows", label: "Windows Server", desc: "Hyper-V, IIS, AD-DC, файловые роли" },
  { name: "shield-lock", label: "Защищённый канал", desc: "Bastion, зашифрованный канал, доступ по контракту" },
];
