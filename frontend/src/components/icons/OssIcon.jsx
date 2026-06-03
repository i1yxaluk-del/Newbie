const PATHS = {
  linux: "",
  prometheus: "M12.005 0a4.6 4.6 0 0 0-2.378.668c1.205-.196 2.715.246 3.434 1.61.84 1.59-.18 3.111.18 4.245.36 1.135 1.346 1.434 1.792 2.355.778-1.135-.36-2.27.18-3.583.42-1.013 1.642-1.345 1.882-2.713-.61-.81-2.084-2.55-5.09-2.582m-5.328 4.45c-.74 1.27-.55 3.143.5 4.53l-.143.123-.063.058q-.105.099-.198.21l-.049.062a2.7 2.7 0 0 0-.158.224l-.029.046q-.075.121-.139.247l-.015.034a2.4 2.4 0 0 0-.244.973l-.005.105a2.4 2.4 0 0 0 .015.301l.002.07c.014.117.039.229.07.34l.015.058q.045.144.108.282l.034.072q.07.137.16.265l.017.025q.087.119.193.227l.049.046q.107.103.226.193l.026.018q.123.087.255.16l.058.029q.146.071.298.123l.029.014q.165.052.34.087l.062.014q.176.032.358.04l.058.005a2.4 2.4 0 0 0 .343-.014l.082-.014q.16-.024.317-.06l.058-.018q.171-.046.331-.117l.058-.026q.135-.06.265-.135l.07-.04c.082-.05.164-.103.244-.155l.07-.054q.121-.09.234-.193l.042-.04q.111-.106.21-.22l.054-.067q.087-.106.166-.226l.04-.058a2.5 2.5 0 0 0 .149-.265l.014-.029a2.4 2.4 0 0 0 .194-.566l.009-.038q.024-.122.04-.247l.005-.07q.014-.127.014-.255v-.04q.001-.156-.014-.31a2.4 2.4 0 0 0-.064-.345l-.002-.014q-.04-.16-.099-.314l-.029-.07a3 3 0 0 0-.143-.299l-.029-.058q-.084-.146-.184-.282l-.04-.05a2.5 2.5 0 0 0-.215-.247l-.04-.04q-.121-.115-.255-.218l-.04-.029-.071-.05-.13-.087c-.08-.05-.165-.094-.252-.137l-.049-.025c-.246-.117-.516-.196-.798-.234l-.029-.005a3 3 0 0 0-.31-.022q-.156-.001-.31.014l-.07.005c-.235.025-.467.072-.687.143l-.058.018q-.286.094-.557.234l-.038.018q-.265.137-.51.314l-.024.018a3.4 3.4 0 0 0-.494.46c-.123-1.117-.196-2.323.55-3.296M12 3.59a8.41 8.41 0 1 0 0 16.82A8.41 8.41 0 0 0 12 3.59m0 1.36a7.05 7.05 0 1 1 0 14.1 7.05 7.05 0 0 1 0-14.1m0 13.13a3.94 3.94 0 0 0 3.94-3.94H8.06A3.94 3.94 0 0 0 12 18.08m-4.78-4.94c-.06 0-.118.005-.176.014v3.05a4.93 4.93 0 0 1-.37-1.86 4.95 4.95 0 0 1 .37-1.875c.058-.005.115-.01.176-.01zm9.56 0c.06 0 .117.005.176.01a4.95 4.95 0 0 1 .37 1.876 4.93 4.93 0 0 1-.37 1.86v-3.05a1 1 0 0 0-.176-.014z",
  wazuh: "M12 2 4 5v6c0 5 3.5 9.5 8 11 4.5-1.5 8-6 8-11V5l-8-3zm0 4.5L17 8v3.5c0 3.5-2.3 6.7-5 7.7-2.7-1-5-4.2-5-7.7V8l5-1.5z",
  ansible: "M12 0a12 12 0 1 0 12 12A12.04 12.04 0 0 0 12 0zM7.71 18.84a1.2 1.2 0 0 1-.51-1.46l4.78-11.45c.18-.43.6-.69 1.06-.66.45.04.83.36.96.79l4.07 11.32c.18.5-.04 1.06-.51 1.32-.5.27-1.13.18-1.51-.22l-3.43-3.59-3.96 3.59c-.32.31-.78.42-1.18.36z",
  puppet: "M5 3h9a5 5 0 0 1 0 10H8v8H5V3zm3 3v4h6a2 2 0 1 0 0-4H8z",
  restic: "M12 2 3 6v6c0 5 3.5 9.5 9 11 5.5-1.5 9-6 9-11V6l-9-4zm0 5 3 3h-2v4h-2v-4H9l3-3z",
  wireguard: "M12 0 1 4v8c0 6 4.6 10.7 11 12 6.4-1.3 11-6 11-12V4L12 0zm0 4 7 2.5V12c0 4.5-3.4 8.4-7 9.5-3.6-1.1-7-5-7-9.5V6.5L12 4z",
  nginx: "M12 0 2 6v12l10 6 10-6V6L12 0zm5 16-3 .8-5-7v6.5L7 17.6V6.4l3-.8 5 7V6.1l2-.5v10.4z",
  docker: "M13.4 8.7h2v2h-2zm0-2.7h2v2h-2zm-2.7 2.7h2v2h-2zm0-2.7h2v2h-2zM8.1 8.7h2v2h-2zM5.4 8.7h2v2h-2zm10.7 2.7h2v2h-2zm0-2.7h2v2h-2zM8.1 6h2v2h-2zM23.7 11c-.3-.2-1.2-.5-2.3-.3-.1-.9-.6-1.7-1.5-2.4l-.5-.3-.3.5c-.4.6-.6 1.4-.5 2.2 0 .3.1.7.3 1-.4.2-1.1.5-2.1.5H1.1c-.4 1.4-.4 5.7 2.4 8.7C5.7 22.5 8.7 24 12.6 24c8.5 0 14.7-3.9 17.6-11.1.4 0 1.2-.1 1.5-.7l.3-.5-.4-.3z",
  samba: "M3 5h4l2 2h13v12H3V5zm2 2v10h14V9H8L6 7H5z",
  postgresql: "M17.13 3c-2.06 0-3.6.92-4.32 2.46-.7-.34-1.36-.46-1.91-.46-1.07 0-2.04.41-2.7 1.13-.66.72-1 1.7-1 2.87 0 .92.11 2.06.34 3.18.21 1.13.51 2.27.85 3.21.34.94.74 1.7 1.16 2.27.41.57.86.92 1.41 1.04.55.13 1.13-.04 1.6-.43.5-.41 1.04-1.07 1.65-2 .55-.83 1.04-1.85 1.46-3.04.21-.6.4-1.21.55-1.83.16.62.34 1.23.55 1.83.41 1.19.92 2.21 1.46 3.04.6.92 1.16 1.59 1.65 2 .47.39 1.04.55 1.6.43.55-.13 1-.47 1.41-1.04.41-.57.83-1.34 1.16-2.27.34-.94.64-2.08.85-3.21.21-1.13.34-2.27.34-3.18 0-1.16-.34-2.16-1-2.87-.66-.72-1.62-1.13-2.7-1.13-.55 0-1.21.13-1.91.46C20.73 3.92 19.18 3 17.13 3z",
  freeipa: "M4 6h6v3H7v9H4V6zm8 0h3v12h-3V6zm5 0h3v12h-3V6z",
  zabbix: "M4 5h16v2.5L8 16.5h12V19H4v-2.5L16 7.5H4V5z",
};

const SHAPES = {
  linux: { kind: "shape", render: () => (
    <>
      <rect x="5" y="3" width="14" height="18" rx="2" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <text x="12" y="11" dominantBaseline="central" textAnchor="middle" fontSize="7" fontFamily="system-ui,sans-serif" fontWeight="800" fill="currentColor">$_</text>
      <path d="M5 15h14" stroke="currentColor" strokeWidth="1" opacity=".4" />
    </>
  ) },
  grafana: { kind: "shape", render: () => (
    <>
      <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <path d="M5 17l4-6 3 4 4-8 3 6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx="5" cy="17" r="1" fill="currentColor" />
      <circle cx="9" cy="11" r="1" fill="currentColor" />
      <circle cx="12" cy="15" r="1" fill="currentColor" />
      <circle cx="16" cy="7" r="1" fill="currentColor" />
      <circle cx="19" cy="13" r="1" fill="currentColor" />
    </>
  ) },
  loki: { kind: "shape", render: () => (
    <>
      <rect x="3" y="3" width="18" height="18" rx="3" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <path d="M7 8h2v8H7zm4-3h2v11h-2zm4 5h2v6h-2z" fill="currentColor" opacity=".7" />
    </>
  ) },
};

export default function OssIcon({ name, size = 24, color = "currentColor", style }) {
  const shape = SHAPES[name];
  if (shape) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" role="img" aria-label={name} style={{ color, ...style }}>
        {shape.render()}
      </svg>
    );
  }
  const path = PATHS[name];
  if (!path) return null;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={color} role="img" aria-label={name} style={style}>
      <path d={path} />
    </svg>
  );
}

export const OSS_TOOLS = [
  { name: "prometheus", label: "Prometheus", desc: "Метрики, time-series, alerts" },
  { name: "grafana", label: "Grafana", desc: "Дашборды для клиента и для нас" },
  { name: "loki", label: "Loki", desc: "Централизованные логи (Silver+)" },
  { name: "wazuh", label: "Wazuh", desc: "SIEM, IDS, FIM (Gold)" },
  { name: "ansible", label: "Ansible", desc: "Bootstrap и IaC" },
  { name: "puppet", label: "Puppet", desc: "Долгоживущие конфиги (Silver+)" },
  { name: "restic", label: "Restic", desc: "AES-256 инкрем. бэкапы в облако" },
  { name: "wireguard", label: "WireGuard", desc: "VPN-mesh клиент ↔ executor" },
  { name: "nginx", label: "Nginx", desc: "Reverse-proxy, TLS, балансировка" },
  { name: "docker", label: "Docker", desc: "Контейнеры приложений" },
  { name: "postgresql", label: "PostgreSQL", desc: "СУБД, ядро Postgres Pro" },
  { name: "samba", label: "Samba", desc: "Файловые шары (SMB)" },
  { name: "freeipa", label: "FreeIPA", desc: "Linux-альтернатива AD (10% клиентов)" },
];
