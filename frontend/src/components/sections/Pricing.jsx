import { Check } from "lucide-react";
import { useContent } from "@/content/useContent";
import { reachGoal } from "@/utils/metrika";

export default function Pricing() {
  const c = useContent().pricing;
  const PLANS = c.plans;

  const onPick = (id) => {
    reachGoal("cta_click", { tariff: id });
    window.dispatchEvent(new CustomEvent("msp:set-tariff", { detail: id }));
    const form = document.getElementById("audit");
    if (form) form.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  return (
    <section
      data-testid="pricing-section"
      id="pricing"
      style={{
        padding: "120px 0",
        background: "#0e0c0a",
        color: "#f5f1e8",
        borderBottom: "1px solid rgba(255,255,255,.06)",
      }}
    >
      <div className="wrap">
        <div className="reveal section-header" style={{ color: "#f5f1e8" }}>
          <div>
            <div
              className="tag-dot"
              style={{ marginBottom: 18, color: "rgba(255,255,255,.55)" }}
            >
              {c.eyebrow}
            </div>
            <h2
              className="h-section"
              style={{ color: "#f5f1e8" }}
            >
              {c.headingBefore}
              <br />
              <em style={{ color: "#5fc9a2", fontStyle: "italic" }}>{c.headingEm}</em>
            </h2>
          </div>
          <p className="section-lead" style={{ color: "rgba(241,237,228,.65)" }}>
            {c.lead}
          </p>
        </div>

        <div
          className="pricing-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3,1fr)",
            gap: 2,
            background: "var(--rule)",
            border: "1px solid var(--rule)",
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
          {PLANS.map((p, i) => (
            <div
              key={p.id}
              data-testid={`plan-${p.id}`}
              className={`reveal ${i > 0 ? `reveal-d${i}` : ""}`}
              style={{
                background: p.featured ? "var(--forest)" : "var(--cream)",
                color: p.featured ? "#fff" : "var(--ink)",
                padding: "38px 32px",
                position: "relative",
                transition: "background .2s",
              }}
            >
              <div
                className="font-mono"
                style={{
                  fontSize: 10.5,
                  letterSpacing: ".14em",
                  textTransform: "uppercase",
                  fontWeight: 500,
                  color: p.featured ? "rgba(255,255,255,.7)" : "var(--stone)",
                  marginBottom: 10,
                }}
              >
                {p.eyebrow}
              </div>
              <div
                className="font-display"
                style={{
                  fontSize: 30,
                  fontWeight: 500,
                  color: p.featured ? "#fff" : "var(--ink)",
                  marginBottom: 4,
                  letterSpacing: "-.01em",
                }}
              >
                {p.name}
              </div>
              <div
                style={{
                  fontSize: 14,
                  color: p.featured ? "rgba(255,255,255,.78)" : "var(--ink-2)",
                  opacity: p.featured ? 1 : 0.78,
                  marginBottom: 28,
                  lineHeight: 1.45,
                  whiteSpace: "pre-line",
                }}
              >
                {p.tagline}
              </div>

              <div
                style={{
                  padding: "20px 0",
                  marginBottom: 22,
                  borderTop: `1px solid ${p.featured ? "rgba(255,255,255,.15)" : "var(--rule)"}`,
                  borderBottom: `1px solid ${p.featured ? "rgba(255,255,255,.15)" : "var(--rule)"}`,
                }}
              >
                 <span
                   style={{
                     fontSize: 11,
                     fontFamily: "var(--fm)",
                     letterSpacing: ".08em",
                     textTransform: "uppercase",
                     color: p.featured ? "rgba(255,255,255,.6)" : "var(--stone)",
                     display: "block",
                     marginBottom: 4,
                   }}
                 >
                   от
                 </span>
                 <div
                   className="font-display"
                   style={{
                     fontSize: 42,
                     fontWeight: 500,
                     color: p.featured ? "#fff" : "var(--ink)",
                     letterSpacing: "-.02em",
                     lineHeight: 1,
                   }}
                 >
                   {p.price}{" "}
                   <span style={{ fontSize: 22, fontWeight: 300 }}>₽</span>
                   <span style={{ fontSize: 11, fontWeight: 400, verticalAlign: "super", lineHeight: 0, marginLeft: 1 }}>*</span>
                   <span style={{ fontSize: 14, fontWeight: 400, marginLeft: 6, color: p.featured ? "rgba(255,255,255,.7)" : "var(--stone)" }}>в месяц</span>
                 </div>
                 <div
                   style={{
                     fontSize: 13,
                     color: p.featured ? "rgba(255,255,255,.7)" : "var(--stone)",
                     marginTop: 4,
                   }}
                 >
                   {p.setup}
                 </div>
              </div>

              <ul style={{ listStyle: "none", padding: 0, marginBottom: 28 }}>
                {p.features.map((f, idx) => (
                  <li
                    key={idx}
                    style={{
                      display: "flex",
                      gap: 12,
                      alignItems: "flex-start",
                      fontSize: 14.5,
                      padding: "10px 0",
                      borderBottom: `1px solid ${p.featured ? "rgba(255,255,255,.10)" : "var(--rule-lt)"}`,
                      color: p.featured ? "rgba(255,255,255,.92)" : "var(--ink-2)",
                      lineHeight: 1.4,
                    }}
                  >
                    <Check
                      size={15}
                      strokeWidth={2.4}
                      color={p.featured ? "#5fc9a2" : "var(--forest)"}
                      style={{ flexShrink: 0, marginTop: 2 }}
                    />
                    <span style={{ fontWeight: f.bold ? 600 : 450 }}>{f.text}</span>
                  </li>
                ))}
              </ul>

               <button
                data-testid={`plan-${p.id}-cta`}
                onClick={() => onPick(p.id)}
                className={p.featured ? "btn-core btn-light" : "btn-core btn-secondary"}
                style={{ width: "100%", padding: 13 }}
              >
                {p.cta}
              </button>
            </div>
          ))}
        </div>

        {c.pricingFootnote && (
          <p style={{ textAlign: "center", fontSize: 12, color: "var(--stone)", marginTop: 16, maxWidth: 700, marginLeft: "auto", marginRight: "auto", lineHeight: 1.5 }}>
            {c.pricingFootnote}
          </p>
        )}
      </div>

      <style>{`
        @media (max-width: 960px) {
          .pricing-grid { grid-template-columns: 1fr !important; background: none !important; border: none !important; gap: 16px !important; }
          .pricing-grid > div { border: 1px solid var(--rule); border-radius: 8px; }
        }
      `}</style>
    </section>
  );
}
