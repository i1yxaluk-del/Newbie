import { useEffect } from "react";
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
import { reachGoal } from "@/utils/metrika";

// v6.3 — Stack replaces TrustStrip:
//   Hero → Stack → Capabilities → Pricing → Process → Pain+Calc → FAQ → CTAForm → FinalCta
export default function Landing() {
  const containerRef = useReveal();

  useEffect(() => {
    let scroll50Fired = false;
    let scrollPricingFired = false;

    const onScroll = () => {
      const scrollPct =
        (window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100;
      if (!scroll50Fired && scrollPct >= 50) {
        scroll50Fired = true;
        reachGoal("scroll_50");
      }
    };

    const pricingEl = document.getElementById("pricing");
    if (pricingEl) {
      const io = new IntersectionObserver(
        ([e]) => {
          if (e.isIntersecting && !scrollPricingFired) {
            scrollPricingFired = true;
            reachGoal("scroll_pricing");
            io.disconnect();
          }
        },
        { threshold: 0.1 },
      );
      io.observe(pricingEl);
    }

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
    };
  }, []);

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
