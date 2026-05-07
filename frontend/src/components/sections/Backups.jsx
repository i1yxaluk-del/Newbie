import { BackupHealth, SlaTimeline } from "@/components/dashboards";

export default function Backups() {
  return (
    <section
      data-testid="backups-section"
      id="backups"
      style={{
        padding: "120px 0",
        background: "var(--cream)",
      }}
    >
      <div className="wrap">
        <div style={{ maxWidth: 760, marginBottom: 56 }}>
          <div className="tag-dot" style={{ marginBottom: 18 }}>
            Сохраняем
          </div>
          <h2 className="h-section" style={{ marginBottom: 20 }}>
            Бэкапы, которые{" "}
            <em>проверяются</em>
            <br />
            каждую неделю.
          </h2>
          <p className="section-lead" style={{ maxWidth: 620 }}>
            Restic, AES-256, инкрементально, в облачном хранилище.
            Автоматический restore-тест 1 раз в неделю —
            иначе бэкап ≠ бэкап.
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0,1.1fr) minmax(0,1fr)",
            gap: 36,
            alignItems: "stretch",
          }}
          className="backups-grid"
        >
          <div>
            <BackupHealth />
          </div>
          <div>
            <SlaTimeline />
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 900px) {
          [data-testid="backups-section"] .backups-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </section>
  );
}
