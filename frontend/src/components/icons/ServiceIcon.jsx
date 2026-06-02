// Managed services — what we administer for clients (vs OssIcon = our tools).
// Geometric monogram marks (no copyrighted logos), 24×24 viewBox.

const SERVICES = {
// Windows Server (4-square)
windows: { kind: "shape", render: (s) => (
  <>
    <rect x="2" y="2"  width="9" height="9" fill="currentColor" />
    <rect x="13" y="2" width="9" height="9" fill="currentColor" />
    <rect x="2" y="13" width="9" height="9" fill="currentColor" />
    <rect x="13" y="13" width="9" height="9" fill="currentColor" />
  </>
) },
// Active Directory (Person + ring)
ad: { kind: "shape", render: () => (
  <>
    <circle cx="12" cy="9" r="3.5" fill="none" stroke="currentColor" strokeWidth="1.6" />
    <path d="M5 21c0-3.5 3.1-6 7-6s7 2.5 7 6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    <circle cx="12" cy="12" r="11" fill="none" stroke="currentColor" strokeWidth="1.2" strokeDasharray="2 2" />
  </>
) },
// 1С — text 1С in box
onec: { kind: "monogram", text: "1С" },
// MS SQL — text Sql
mssql: { kind: "monogram", text: "SQL" },
// Exchange — envelope @
mail: { kind: "shape", render: () => (
  <>
    <rect x="2" y="5" width="20" height="14" rx="2" fill="none" stroke="currentColor" strokeWidth="1.6" />
    <path d="M2 7l10 7 10-7" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
  </>
) },
// File server — folder
fileserver: { kind: "shape", render: () => (
  <>
    <path
      d="M3 6a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6z"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinejoin="round"
    />
    <path d="M3 10h18" stroke="currentColor" strokeWidth="1" />
  </>
) },
// Web — globe
web: { kind: "shape", render: () => (
  <>
    <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="1.6" />
    <path d="M2 12h20" stroke="currentColor" strokeWidth="1.4" />
    <path
      d="M12 2c3 3 4 7 4 10s-1 7-4 10c-3-3-4-7-4-10s1-7 4-10z"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
    />
  </>
) },
// Database — cylinder
database: { kind: "shape", render: () => (
  <>
    <ellipse cx="12" cy="5" rx="9" ry="3" fill="none" stroke="currentColor" strokeWidth="1.6" />
    <path
      d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
    />
    <path d="M3 12c0 1.7 4 3 9 3s9-1.3 9-3" fill="none" stroke="currentColor" strokeWidth="1.4" />
  </>
) },
// VPN — lock + key
vpn: { kind: "shape", render: () => (
  <>
    <rect
      x="4"
      y="11"
      width="16"
      height="10"
      rx="2"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
    />
    <path
      d="M8 11V8a4 4 0 1 1 8 0v3"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
    />
  </>
) },
// Shield-lock — secure management channel (bastion / AmneziaWG, contracts only)
"shield-lock": { kind: "shape", render: () => (
  <>
    <path
      d="M12 2.5L4 5v6c0 5 3.5 8.5 8 10.5 4.5-2 8-5.5 8-10.5V5l-8-2.5z"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinejoin="round"
    />
    <rect
      x="9"
      y="11.5"
      width="6"
      height="5"
      rx="0.8"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
    />
    <path
      d="M10.5 11.5V10a1.5 1.5 0 0 1 3 0v1.5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
    />
  </>
) },
// Server rack — 3 stacked rectangles
server: { kind: "shape", render: () => (
  <>
    <rect x="3" y="4"  width="18" height="5" rx="1" fill="none" stroke="currentColor" strokeWidth="1.6" />
    <rect x="3" y="10" width="18" height="5" rx="1" fill="none" stroke="currentColor" strokeWidth="1.6" />
    <rect x="3" y="16" width="18" height="5" rx="1" fill="none" stroke="currentColor" strokeWidth="1.6" />
    <circle cx="6" cy="6.5" r=".7" fill="currentColor" />
    <circle cx="6" cy="12.5" r=".7" fill="currentColor" />
    <circle cx="6" cy="18.5" r=".7" fill="currentColor" />
  </>
) },
// Hyper-V / virtualization — stacked H
virt: { kind: "monogram", text: "VM" },
// IIS — text IIS
iis: { kind: "monogram", text: "IIS" },
// Distributed cloud storage — cloud + nodes
cloud: { kind: "shape", render: () => (
  <>
    <path
      d="M7 17h10a4 4 0 0 0 .5-7.97A6 6 0 0 0 6 10 4 4 0 0 0 7 17z"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinejoin="round"
    />
    <circle cx="9" cy="14" r="1.1" fill="currentColor" />
    <circle cx="12" cy="14" r="1.1" fill="currentColor" />
    <circle cx="15" cy="14" r="1.1" fill="currentColor" />
  </>
) },
// Telegram (paper-plane) — used as channel mark
telegram: { kind: "shape", render: () => (
  <>
    <path
      d="M21.5 3.5L2.5 11l6 2.5L17 7l-6.5 8 1 5 3-3 4 3z"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinejoin="round"
      strokeLinecap="round"
    />
  </>
) },
// MAX (мессенджер) — rounded square + M
max: { kind: "shape", render: () => (
  <>
    <rect
      x="2"
      y="2"
      width="20"
      height="20"
      rx="5"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
    />
    <text
      x="12"
      y="12"
      dominantBaseline="central"
      textAnchor="middle"
      fontSize="11"
      fontFamily="var(--fb), system-ui, sans-serif"
      fontWeight="700"
      fill="currentColor"
      letterSpacing="-0.04em"
    >
      M
    </text>
  </>
) },
// "и другие" — three dots in rounded box
more: { kind: "shape", render: () => (
  <>
    <rect
      x="2"
      y="2"
      width="20"
      height="20"
      rx="4"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeDasharray="2 3"
    />
    <circle cx="7.5" cy="12" r="1.2" fill="currentColor" />
    <circle cx="12" cy="12" r="1.2" fill="currentColor" />
    <circle cx="16.5" cy="12" r="1.2" fill="currentColor" />
  </>
) },
};

export default function ServiceIcon({ name, size = 24, color = "currentColor", style }) {
const m = SERVICES[name];
if (!m) return null;

if (m.kind === "monogram") {
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label={name}
      style={{ color, ...style }}
    >
      <rect
        x="1"
        y="1"
        width={size - 2}
        height={size - 2}
        rx="3"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
      />
      <text
        x={size / 2}
        y={size / 2}
        dominantBaseline="central"
        textAnchor="middle"
        fontSize={size * 0.42}
        fontFamily="var(--fb), system-ui, sans-serif"
        fontWeight="600"
        fill="currentColor"
        letterSpacing="-.02em"
      >
        {m.text}
      </text>
    </svg>
  );
}

return (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    role="img"
    aria-label={name}
    style={{ color, ...style }}
  >
    {m.render(size)}
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
{ name: "shield-lock", label: "Защищённый канал управления", desc: "Bastion, зашифрованный канал, доступ по контракту" },
];
