import useReveal from "@/hooks/useReveal";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import BackToTop from "@/components/BackToTop";
import Hero from "@/components/sections/Hero";
import TrustStrip from "@/components/sections/TrustStrip";
import Visibility from "@/components/sections/Visibility";
import Alerts from "@/components/sections/Alerts";
import Backups from "@/components/sections/Backups";
import Stack from "@/components/sections/Stack";
import Pain from "@/components/sections/Pain";
import Pricing from "@/components/sections/Pricing";
import Process from "@/components/sections/Process";
import FAQ from "@/components/sections/FAQ";
import CTAForm from "@/components/sections/CTAForm";
import FinalCta from "@/components/sections/FinalCta";

// v6.0 — Antimetal-style:
//   Hero (DashboardWide) → Trust (services + tools)
//   → Visibility (Latency dashboard) — light
//   → Alerts (Telegram + Wazuh)      — DARK
//   → Backups (BackupHealth + SLA)
//   → Stack (services + OSS + RU)
//   → Pricing → Process → Pain+Calc → FAQ → CTAForm
//   → FinalCta — DARK
export default function Landing() {
  const containerRef = useReveal();
  return (
    <div ref={containerRef} data-testid="landing-root">
      <Nav />
      <Hero />
      <TrustStrip />
      <Visibility />
      <Alerts />
      <Backups />
      <Stack />
      <Pricing />
      <Process />
      <Pain />
      <FAQ />
      <CTAForm />
      <FinalCta />
      <Footer />
      <BackToTop />
    </div>
  );
}
