import useReveal from "@/hooks/useReveal";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import BackToTop from "@/components/BackToTop";
import Hero from "@/components/sections/Hero";
import TrustStrip from "@/components/sections/TrustStrip";
import Capabilities from "@/components/sections/Capabilities";
import Pain from "@/components/sections/Pain";
import Pricing from "@/components/sections/Pricing";
import Process from "@/components/sections/Process";
import FAQ from "@/components/sections/FAQ";
import CTAForm from "@/components/sections/CTAForm";
import FinalCta from "@/components/sections/FinalCta";

// v6.2 — горизонтальный pane:
//   Hero → Trust
//   → Capabilities (Видим · Реагируем · Сохраняем · Стек) — горизонтальная карусель
//   → Pricing → Process → Pain+Calc → FAQ → CTAForm
//   → FinalCta
export default function Landing() {
  const containerRef = useReveal();
  return (
    <div ref={containerRef} data-testid="landing-root">
      <Nav />
      <Hero />
      <TrustStrip />
      <Capabilities />
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
