import { OssIcon, RuIcon, ServiceIcon } from "@/components/icons";
import { useContent } from "@/content/useContent";

// Services row defaults: kind="service". Tools row mixes kind=oss/ru/service.
function iconFor({ kind = "service", icon }) {
  if (kind === "oss") return <OssIcon name={icon} size={28} />;
  if (kind === "ru") return <RuIcon name={icon} size={28} />;
  return <ServiceIcon name={icon} size={28} />;
}

function Row({ label, items, gridCols }) {
  return (
    <div style={{ marginBottom: 32 }}>
      <div
        className="tag-dot"
        style={{
          marginBottom: 18,
          justifyContent: "center",
          display: "flex",
        }}
      >
        {label}
      </div>
      <div
        className="trust-strip-grid"
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${gridCols}, minmax(0, 1fr))`,
          gap: 16,
          alignItems: "center",
        }}
      >
        {items.map((it) => (
          <div
            key={it.label}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 8,
              color: "var(--ink-2)",
              opacity: 1,
            }}
          >
            <div style={{ height: 28, display: "flex", alignItems: "center" }}>
              {iconFor(it)}
            </div>
            <div
              style={{
                fontFamily: "var(--fm)",
                fontSize: 10.5,
                color: "var(--stone)",
                fontWeight: 500,
                letterSpacing: ".04em",
                textAlign: "center",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
                maxWidth: "100%",
              }}
            >
              {it.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function TrustStrip() {
  const c = useContent().trust;
  const services = c.services.map((it) => ({ ...it, kind: "service" }));
  return (
    <section
      data-testid="trust-strip"
      style={{
        padding: "64px 0 48px",
        background: "var(--cream)",
        borderTop: "1px solid var(--rule-lt)",
        borderBottom: "1px solid var(--rule-lt)",
      }}
    >
      <div className="wrap">
        <Row label={c.servicesLabel} items={services} gridCols={services.length} />
        <Row label={c.toolsLabel} items={c.tools} gridCols={c.tools.length} />
      </div>
      <style>{`
        @media (max-width: 1080px) {
          [data-testid="trust-strip"] .trust-strip-grid {
            grid-template-columns: repeat(5, minmax(0, 1fr)) !important;
            gap: 24px 12px !important;
          }
        }
        @media (max-width: 720px) {
          [data-testid="trust-strip"] .trust-strip-grid {
            grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
          }
        }
        @media (max-width: 480px) {
          [data-testid="trust-strip"] .trust-strip-grid {
            grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
          }
        }
      `}</style>
    </section>
  );
}
