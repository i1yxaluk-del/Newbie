import { useCallback, useEffect, useRef, useState } from "react";
import {
  LatencyChart,
  TelegramAlert,
  WazuhAlerts,
  BackupHealth,
  SlaTimeline,
} from "@/components/dashboards";
import {
  OssIcon,
  OSS_TOOLS,
  RuIcon,
  RU_TOOLS,
  ServiceIcon,
  SERVICE_LIST,
} from "@/components/icons";

const PANELS = [
  { id: "visibility", tag: "Видим", title: "Один дашборд", em: "на всю инфраструктуру" },
  { id: "alerts", tag: "Реагируем", title: "Когда что-то ломается —", em: "вы узнаёте первыми" },
  { id: "backups", tag: "Сохраняем", title: "Бэкапы, которые", em: "проверяются каждую неделю" },
  { id: "stack", tag: "Стек", title: "Что мы обслуживаем", em: "и чем обслуживаем" },
];

function Bullet({ children }) {
  return (
    <li
      style={{
        display: "flex",
        gap: 12,
        fontSize: 14.5,
        color: "var(--ink-2)",
        lineHeight: 1.5,
      }}
    >
      <span
        aria-hidden="true"
        style={{
          flex: "0 0 auto",
          width: 16,
          height: 1,
          background: "var(--forest)",
          marginTop: 11,
        }}
      />
      <span>{children}</span>
    </li>
  );
}

function PanelShell({ tag, title, em, children, dark }) {
  return (
    <article
      className="cap-panel"
      data-panel-id={tag}
    >
      <div className="cap-inner">
        <div className="cap-text">
          <h3
            className="h-section cap-title"
            style={{
              margin: 0,
              marginBottom: 18,
              fontSize: "clamp(32px, 4vw, 52px)",
              lineHeight: 1.05,
              color: dark ? "#f5f1e8" : "var(--ink)",
            }}
          >
            {title}{" "}
            <em
              style={{
                fontStyle: "italic",
                color: dark ? "#5fc9a2" : "var(--forest)",
              }}
            >
              {em}.
            </em>
          </h3>
          {children.text}
        </div>
        <div className="cap-visual">{children.visual}</div>
      </div>
    </article>
  );
}

function VisibilityPanel() {
  return (
    <PanelShell tag="Видим" title="Один дашборд" em="на всю инфраструктуру">
      {{
        text: (
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 12 }}>
            <Bullet>Метрики, логи, алерты — в одном Grafana-окне</Bullet>
            <Bullet>Read-only доступ для клиента</Bullet>
          </ul>
        ),
        visual: <LatencyChart />,
      }}
    </PanelShell>
  );
}

function AlertsPanel() {
  const bulletStyle = {
    display: "flex",
    gap: 12,
    fontSize: 14.5,
    color: "rgba(241,237,228,.78)",
    lineHeight: 1.5,
  };
  const dashStyle = {
    flex: "0 0 auto",
    width: 16,
    height: 1,
    background: "#5fc9a2",
    marginTop: 11,
  };
  return (
    <article
      className="cap-panel cap-panel-dark"
      data-panel-id="Реагируем"
    >
      <div className="cap-inner">
        <div className="cap-text">
          <h3
            className="h-section cap-title"
            style={{
              margin: 0,
              marginBottom: 18,
              fontSize: "clamp(32px, 4vw, 52px)",
              lineHeight: 1.05,
              color: "#f5f1e8",
            }}
          >
            Когда что-то ломается —{" "}
            <em style={{ fontStyle: "italic", color: "#5fc9a2" }}>вы узнаёте первыми.</em>
          </h3>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 12 }}>
            <li style={bulletStyle}>
              <span aria-hidden="true" style={dashStyle} />
              <span>Алерты в согласованных каналах · ACK · silence · runbook</span>
            </li>
            <li style={bulletStyle}>
              <span aria-hidden="true" style={dashStyle} />
              <span>Gold — SIEM Wazuh с автоблокировкой</span>
            </li>
          </ul>
        </div>
        <div className="cap-visual cap-visual-stack">
          <TelegramAlert />
          <WazuhAlerts />
        </div>
      </div>
    </article>
  );
}

function BackupsPanel() {
  return (
    <PanelShell tag="Сохраняем" title="Бэкапы, которые" em="проверяются каждую неделю">
      {{
        text: (
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 12 }}>
            <Bullet>Restic, AES-256, в облачное хранилище</Bullet>
            <Bullet>Автоматический restore-тест каждую неделю</Bullet>
          </ul>
        ),
        visual: (
          <div className="cap-visual-stack">
            <BackupHealth />
            <SlaTimeline />
          </div>
        ),
      }}
    </PanelShell>
  );
}

function StackColumn({ title, tag, kind, items, max = 6 }) {
  const Icon =
    kind === "oss" ? OssIcon : kind === "ru" ? RuIcon : ServiceIcon;
  const visible = items.slice(0, max);
  const more = items.length - visible.length;
  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid var(--rule)",
        borderRadius: 8,
        padding: "20px 18px",
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          marginBottom: 4,
          paddingBottom: 10,
          borderBottom: "1px solid var(--rule-lt)",
          gap: 8,
        }}
      >
        <h4
          className="font-display"
          style={{
            fontSize: 16,
            margin: 0,
            fontWeight: 500,
            letterSpacing: "-.01em",
            color: "var(--ink)",
          }}
        >
          {title}
        </h4>
        <span
          className="tag-dot"
          style={{ fontSize: 9.5, color: "var(--stone-lt)" }}
        >
          {tag}
        </span>
      </div>
      <ul
        style={{
          listStyle: "none",
          padding: 0,
          margin: 0,
          display: "grid",
          gap: 10,
        }}
      >
        {visible.map((it) => (
          <li
            key={it.name}
            style={{
              display: "grid",
              gridTemplateColumns: "22px 1fr",
              gap: 10,
              alignItems: "center",
            }}
          >
            <Icon name={it.name} size={20} />
            <span
              style={{
                fontSize: 13,
                color: "var(--ink)",
                fontFamily: "var(--fb)",
                fontWeight: 500,
              }}
            >
              {it.label}
            </span>
          </li>
        ))}
      </ul>
      {more > 0 && (
        <div
          style={{
            fontSize: 11,
            color: "var(--stone-lt)",
            fontFamily: "var(--fm)",
            letterSpacing: ".05em",
            textTransform: "uppercase",
            marginTop: 2,
          }}
        >
          + ещё {more}
        </div>
      )}
    </div>
  );
}

function StackPanel() {
  return (
    <article className="cap-panel" data-panel-id="Стек">
      <div className="cap-inner">
        <div className="cap-text">
          <h3
            className="h-section cap-title"
            style={{
              margin: 0,
              marginBottom: 18,
              fontSize: "clamp(32px, 4vw, 52px)",
              lineHeight: 1.05,
            }}
          >
            Открытый код.{" "}
            <em style={{ fontStyle: "italic", color: "var(--forest)" }}>РФ-реестр.</em>
          </h3>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 12 }}>
            <Bullet>Без vendor lock-in</Bullet>
            <Bullet>152-ФЗ · реестр Минцифры</Bullet>
          </ul>
        </div>
        <div
          className="cap-visual cap-stack-cols"
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr 1fr",
            gap: 12,
            alignItems: "stretch",
          }}
        >
          <StackColumn
            title="Сервисы клиента"
            tag="Что админим"
            kind="service"
            items={SERVICE_LIST}
          />
          <StackColumn
            title="Open source"
            tag="Чем админим"
            kind="oss"
            items={OSS_TOOLS}
          />
          <StackColumn
            title="Реестр Минцифры"
            tag="РФ ПО"
            kind="ru"
            items={RU_TOOLS}
          />
        </div>
      </div>
    </article>
  );
}

export default function Capabilities() {
  const trackRef = useRef(null);
  const [active, setActive] = useState(0);
  const [progress, setProgress] = useState(0);

  // Track scroll position → active panel + progress bar
  useEffect(() => {
    const track = trackRef.current;
    if (!track) return;
    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const w = track.clientWidth;
        const x = track.scrollLeft;
        const max = track.scrollWidth - w;
        const idx = Math.round(x / w);
        setActive(idx);
        setProgress(max > 0 ? Math.min(1, x / max) : 0);
      });
    };
    track.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => {
      track.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(raf);
    };
  }, []);

  const goTo = useCallback((i) => {
    const track = trackRef.current;
    if (!track) return;
    track.scrollTo({ left: i * track.clientWidth, behavior: "smooth" });
  }, []);

  // Match track height to active panel — eliminates empty space below short panels
  useEffect(() => {
    const track = trackRef.current;
    if (!track) return;
    const sync = () => {
      const panel = track.children[active];
      if (!panel) return;
      // Use the panel's content height — track collapses to active panel size.
      // height (not min-height) overrides the grid row max-height behavior.
      track.style.height = panel.offsetHeight + "px";
    };
    sync();
    const ro = new ResizeObserver(sync);
    Array.from(track.children).forEach((c) => ro.observe(c));
    window.addEventListener("resize", sync);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", sync);
    };
  }, [active]);

  // Keyboard arrows when section in viewport
  useEffect(() => {
    const onKey = (e) => {
      if (e.target && e.target.tagName === "INPUT") return;
      if (e.target && e.target.tagName === "TEXTAREA") return;
      const track = trackRef.current;
      if (!track) return;
      const rect = track.getBoundingClientRect();
      const inView =
        rect.top < window.innerHeight * 0.85 && rect.bottom > window.innerHeight * 0.15;
      if (!inView) return;
      if (e.key === "ArrowRight") {
        e.preventDefault();
        goTo(Math.min(PANELS.length - 1, active + 1));
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        goTo(Math.max(0, active - 1));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, goTo]);

  return (
    <section
      data-testid="capabilities-section"
      id="capabilities"
      style={{
        padding: "96px 0 84px",
        background: "var(--cream)",
        borderTop: "1px solid var(--rule-lt)",
      }}
    >
      <div className="wrap" style={{ marginBottom: 36 }}>
        <h2
          className="h-section"
          style={{ margin: 0, fontSize: "clamp(36px, 4.8vw, 64px)" }}
        >
          Видим. <em style={{ fontStyle: "italic" }}>Реагируем.</em> Сохраняем.
        </h2>
      </div>

      {/* Tabs — segmented pill control */}
      <div className="wrap" style={{ marginBottom: 22 }}>
        <div
          role="tablist"
          aria-label="Возможности"
          className="cap-tabs"
        >
          {PANELS.map((p, i) => {
            const isActive = i === active;
            return (
              <button
                key={p.id}
                role="tab"
                type="button"
                aria-selected={isActive}
                onClick={() => goTo(i)}
                data-testid={`cap-tab-${p.id}`}
                className={`cap-tab ${isActive ? "is-active" : ""}`}
              >
                <span
                  className="cap-tab-num"
                  aria-hidden="true"
                >
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="cap-tab-label">{p.tag}</span>
              </button>
            );
          })}
        </div>
        <div className="cap-progress" aria-hidden="true">
          <div
            className="cap-progress-bar"
            style={{ transform: `scaleX(${progress})` }}
          />
        </div>
      </div>

      {/* Carousel track */}
      <div
        ref={trackRef}
        className="cap-track"
        data-testid="capabilities-track"
        tabIndex={0}
        aria-roledescription="carousel"
      >
        <VisibilityPanel />
        <AlertsPanel />
        <BackupsPanel />
        <StackPanel />
      </div>

      <style>{`
        /* Segmented pill control. Active tab = filled forest with cream label.
           Inactive = clearly readable on cream-deep track. */
        .cap-tabs {
          display: inline-flex;
          gap: 0;
          padding: 5px;
          background: var(--cream-deep);
          border: 1px solid var(--rule);
          border-radius: 999px;
          overflow-x: auto;
          scrollbar-width: none;
          -ms-overflow-style: none;
          margin-bottom: 14px;
          max-width: 100%;
        }
        .cap-tabs::-webkit-scrollbar { display: none; }
        .cap-tab {
          flex: 0 0 auto;
          background: transparent;
          border: 0;
          border-radius: 999px;
          padding: 10px 18px;
          font-family: var(--fb);
          font-size: 13.5px;
          font-weight: 500;
          color: var(--ink-2);
          letter-spacing: .005em;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          line-height: 1;
          transition: background .18s ease, color .18s ease, transform .18s ease;
        }
        .cap-tab:hover { background: rgba(26, 24, 21, 0.06); }
        .cap-tab.is-active {
          background: var(--ink);
          color: var(--cream);
          box-shadow: 0 1px 0 rgba(255, 255, 255, 0.08) inset, 0 1px 2px rgba(0,0,0,0.12);
        }
        .cap-tab.is-active:hover { background: var(--ink-2); }
        .cap-tab-num {
          font-family: var(--fm);
          font-size: 11px;
          opacity: .65;
          font-feature-settings: "tnum";
          font-weight: 500;
          letter-spacing: .02em;
        }
        .cap-tab.is-active .cap-tab-num { opacity: .8; }
        .cap-progress {
          height: 2px;
          background: var(--rule);
          position: relative;
          overflow: hidden;
          border-radius: 2px;
        }
        .cap-progress-bar {
          position: absolute;
          inset: 0;
          background: var(--forest);
          transform-origin: left center;
          transform: scaleX(0);
          transition: transform .25s ease;
          border-radius: 2px;
        }
        .cap-track {
          display: flex;
          flex-direction: row;
          align-items: flex-start;
          overflow-x: auto;
          overflow-y: hidden;
          scroll-snap-type: x mandatory;
          scrollbar-width: none;
          -ms-overflow-style: none;
          scroll-behavior: smooth;
          outline: none;
          transition: height .25s ease;
        }
        .cap-track::-webkit-scrollbar { display: none; }
        .cap-panel { flex: 0 0 100%; width: 100%; }
        @media (prefers-reduced-motion: reduce) {
          .cap-track { scroll-behavior: auto; }
        }

        .cap-panel {
          scroll-snap-align: start;
          scroll-snap-stop: always;
          padding: 24px 0 56px;
          content-visibility: auto;
          contain-intrinsic-size: 1px 540px;
        }
        .cap-panel-dark {
          background: #0f0e0c;
        }
        .cap-inner {
          width: min(1240px, calc(100% - 48px));
          margin: 0 auto;
          display: grid;
          grid-template-columns: minmax(260px, 1fr) minmax(0, 1.6fr);
          gap: 64px;
          align-items: start;
          padding: 24px 0;
        }
        .cap-panel-dark .cap-inner { padding: 40px 32px; border-radius: 8px; }
        .cap-text {
          display: flex;
          flex-direction: column;
        }
        .cap-visual { min-width: 0; }
        .cap-visual-stack {
          display: grid;
          gap: 16px;
        }
        .cap-stack-cols { display: grid; }

        @media (max-width: 1080px) {
          .cap-panel { padding: 16px 0 40px; }
          .cap-inner {
            grid-template-columns: 1fr;
            gap: 32px;
            padding: 24px 0;
          }
          .cap-panel-dark .cap-inner { padding: 32px 20px; }
          .cap-stack-cols {
            grid-template-columns: 1fr 1fr !important;
          }
        }
        @media (max-width: 720px) {
          .cap-stack-cols {
            grid-template-columns: 1fr !important;
          }
          .cap-tab { padding: 9px 14px; font-size: 12.5px; gap: 6px; }
          .cap-tab-num { font-size: 10px; }
        }
      `}</style>
    </section>
  );
}
