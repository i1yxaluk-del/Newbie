import useReveal from "@/hooks/useReveal";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import Hero from "@/components/sections/Hero";
import TrustStrip from "@/components/sections/TrustStrip";
import Stack from "@/components/sections/Stack";
import Pain from "@/components/sections/Pain";
import Pricing from "@/components/sections/Pricing";
import Process from "@/components/sections/Process";
import FAQ from "@/components/sections/FAQ";
import CTAForm from "@/components/sections/CTAForm";

// v5.0 — Antimetal-style: Hero с табами (Видим/Реагируем/Сохраняем) → Trust →
// Stack (открытое ПО + РФ ПО) → Pricing → Process → Pain+Calc → FAQ → CTA.
export default function Landing() {
  const containerRef = useReveal();
  return (
    <div ref={containerRef} data-testid="landing-root">
      <Nav />
      <Hero />
      <TrustStrip />
      <Stack />
      <Pricing />
      <Process />
      <Pain />
      <FAQ />
      <CTAForm />
      <Footer />
    </div>
  );
}
