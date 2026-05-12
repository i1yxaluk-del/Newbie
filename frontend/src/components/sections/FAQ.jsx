import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";
import { useContent } from "@/content/useContent";

export default function FAQ() {
  const c = useContent().faq;
  const QA = c.items;
  return (
    <section
      data-testid="faq-section"
      id="faq"
      style={{ padding: "104px 0", borderBottom: "1px solid var(--rule)" }}
    >
      <div className="wrap wrap-sm">
        <div className="reveal" style={{ textAlign: "center", marginBottom: 48 }}>
          <div
            className="tag-dot"
            style={{ marginBottom: 18, justifyContent: "center" }}
          >
            {c.eyebrow}
          </div>
          <h2 className="h-section">
            {c.headingBefore} <em>{c.headingEm}</em>
          </h2>
        </div>

        <Accordion
          type="single"
          collapsible
          className="reveal"
          data-testid="faq-accordion"
          style={{
            background: "#fff",
            border: "1px solid var(--rule)",
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
          {QA.map((item, i) => (
            <AccordionItem
              key={i}
              value={`q-${i}`}
              data-testid={`faq-item-${i}`}
              style={{
                borderBottom: i === QA.length - 1 ? "none" : "1px solid var(--rule-lt)",
              }}
            >
              <AccordionTrigger
                style={{
                  padding: "22px 28px",
                  fontFamily: "var(--fd)",
                  fontSize: 18,
                  fontWeight: 500,
                  color: "var(--ink)",
                  letterSpacing: "-.01em",
                  textAlign: "left",
                }}
              >
                {item.q}
              </AccordionTrigger>
              <AccordionContent
                style={{
                  padding: "0 28px 22px",
                  fontFamily: "var(--fb)",
                  fontSize: 14.5,
                  color: "var(--stone)",
                  lineHeight: 1.7,
                }}
              >
                {item.a}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
}
