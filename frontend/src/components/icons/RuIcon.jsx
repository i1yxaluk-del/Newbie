// Russian (registered in Минцифры) software marks.
// Render as monogram + accent geometry: minimalist, brand-safe (no copyrighted logos),
// each pulls a Cyrillic letter from the product name into a 24×24 mark.

const MARKS = {
  // А — Astra Linux (square with A)
  astra: { letter: "А", shape: "square" },
  // R — RED OS (circle with R)
  redos: { letter: "R", shape: "circle" },
  // А — ALT Linux (rotated square / diamond with A)
  alt: { letter: "А", shape: "diamond" },
  // P — Postgres Pro (rounded square with P)
  postgrespro: { letter: "P", shape: "rounded" },
  // 1С — 1С:Предприятие (square with 1С)
  onec: { letter: "1С", shape: "square", small: true },
  // K — Kaspersky (circle with K)
  kaspersky: { letter: "K", shape: "circle" },
  // О — РФ Облако (распределённое облачное хранилище в РФ)
  rucloud: { letter: "О", shape: "rounded" },
  // M — MyOffice (rounded square with M)
  myoffice: { letter: "M", shape: "rounded" },
  // O — OnlyOffice (circle with O)
  onlyoffice: { letter: "O", shape: "circle" },
  // Б — Bitrix24 (square with Б)
  bitrix: { letter: "Б", shape: "square" },
};

export default function RuIcon({ name, size = 24, color = "currentColor", style }) {
  const m = MARKS[name];
  if (!m) {
    return null;
  }
  const stroke = "currentColor";
  const fontSize = m.small ? size * 0.42 : size * 0.55;
  const transform = m.shape === "diamond" ? `rotate(45 ${size / 2} ${size / 2})` : undefined;

  let shapeEl;
  if (m.shape === "circle") {
    shapeEl = (
      <circle
        cx={size / 2}
        cy={size / 2}
        r={size / 2 - 1}
        fill="none"
        stroke={stroke}
        strokeWidth="1.4"
      />
    );
  } else if (m.shape === "rounded") {
    shapeEl = (
      <rect
        x="1"
        y="1"
        width={size - 2}
        height={size - 2}
        rx="5"
        fill="none"
        stroke={stroke}
        strokeWidth="1.4"
      />
    );
  } else if (m.shape === "diamond") {
    shapeEl = (
      <rect
        x="3"
        y="3"
        width={size - 6}
        height={size - 6}
        fill="none"
        stroke={stroke}
        strokeWidth="1.4"
        transform={transform}
      />
    );
  } else {
    shapeEl = (
      <rect
        x="1"
        y="1"
        width={size - 2}
        height={size - 2}
        rx="2"
        fill="none"
        stroke={stroke}
        strokeWidth="1.4"
      />
    );
  }

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label={name}
      style={{ color, ...style }}
    >
      {shapeEl}
      <text
        x={size / 2}
        y={size / 2}
        dominantBaseline="central"
        textAnchor="middle"
        fontSize={fontSize}
        fontFamily="var(--fb), system-ui, sans-serif"
        fontWeight="600"
        fill={stroke}
        letterSpacing="-0.02em"
      >
        {m.letter}
      </text>
    </svg>
  );
}

export const RU_TOOLS = [
  { name: "astra", label: "Astra Linux", desc: "Сертифицированная ОС, реестр Минцифры №4413" },
  { name: "redos", label: "RED OS", desc: "Российская серверная ОС, реестр №3637" },
  { name: "alt", label: "ALT Linux", desc: "Серверная ОС, реестр №4012" },
  { name: "postgrespro", label: "Postgres Pro", desc: "Российская СУБД, реестр №116" },
  { name: "onec", label: "1С:Предприятие", desc: "ERP, бухгалтерия, документооборот" },
  { name: "kaspersky", label: "Kaspersky Endpoint", desc: "Антивирус и EDR (Gold), реестр №108–115" },
  { name: "rucloud", label: "РФ Облако", desc: "Распределённое облачное хранилище, 152-ФЗ" },
  { name: "myoffice", label: "МойОфис", desc: "Офисный пакет, реестр №216" },
  { name: "onlyoffice", label: "ONLYOFFICE", desc: "Российский разработчик, реестр №10399" },
  { name: "bitrix", label: "Bitrix24", desc: "CRM/портал, российская разработка" },
];
