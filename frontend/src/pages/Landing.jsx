import useReveal from "@/hooks/useReveal";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import BackToTop from "@/components/BackToTop";
import Hero from "@/components/sections/Hero";
import Stack from "@/components/sections/Stack";
import Capabilities from "@/components/sections/Capabilities";
import Pain from "@/components/sections/Pain";
import Pricing from "@/components/sections/Pricing";
import Process from "@/components/sections/Process";
import FAQ from "@/components/sections/FAQ";
import CTAForm from "@/components/sections/CTAForm";
import FinalCta from "@/components/sections/FinalCta";

// v6.3 — Stack replaces TrustStrip:
//   Hero → Stack → Capabilities → Pricing → Process → Pain+Calc → FAQ → CTAForm → FinalCta
export default function Landing() {
  const containerRef = useReveal();
  return (
    <div ref={containerRef} data-testid="landing-root">
      <Nav />
      <Hero />
      <Stack />
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
