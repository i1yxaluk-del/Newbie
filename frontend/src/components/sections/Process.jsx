import { useContent } from "@/content/useContent";

export default function Process() {
  const c = useContent().process;
  const STEPS = c.steps;
  return (
    <section
      data-testid="process-section"
      id="process"
      style={{
        padding: "104px 0",
        background: "var(--cream)",
        borderBottom: "1px solid var(--rule)",
      }}
    >
      <div className="wrap">
        <div className="reveal section-header">
          <div>
            <div className="tag-dot" style={{ marginBottom: 18 }}>
              {c.eyebrow}
            </div>
            <h2 className="h-section">
              {c.headingBefore} <em>{c.headingEm}</em>
              <br />
              {c.headingAfter}
            </h2>
          </div>
          <p className="section-lead">{c.lead}</p>
        </div>

        <div className="process-steps">
          {STEPS.map((s, i) => (
            <div
              key={s.date}
              data-testid={`process-step-${i}`}
              className={`reveal process-step ${i > 0 ? `reveal-d${i % 3}` : ""}`}
              style={{
                borderBottom: i === STEPS.length - 1 ? "none" : "1px solid var(--rule-lt)",
              }}
            >
              <div className="process-step-date">
                <span
                  className="font-display"
                  style={{
                    fontSize: 22,
                    fontWeight: 500,
                    color: "var(--ink)",
                    letterSpacing: "-.01em",
                  }}
                >
                  {s.date}
                </span>
              </div>
              <div>
                <h3
                  className="font-display"
                  style={{
                    fontSize: 22,
                    fontWeight: 500,
                    color: "var(--ink)",
                    marginBottom: 6,
                    letterSpacing: "-.01em",
                  }}
                >
                  {s.title}
                </h3>
                <p
                  style={{
                    fontSize: 15,
                    color: "var(--stone)",
                    lineHeight: 1.7,
                    maxWidth: 760,
                  }}
                >
                  {s.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        .process-steps { position: relative; }
        .process-step {
          display: grid;
          grid-template-columns: 200px minmax(0, 1fr);
          gap: 40px;
          padding: 28px 0;
          align-items: start;
        }
        .process-step > * { min-width: 0; }
        .process-step-date {
          display: flex;
          align-items: center;
          gap: 14px;
          color: var(--stone);
        }
        @media (max-width: 720px) {
          .process-step {
            grid-template-columns: 1fr;
            gap: 8px;
            padding: 24px 0;
          }
          .process-step-date span { font-size: 16px !important; color: var(--stone); }
        }
      `}</style>
    </section>
  );
}
