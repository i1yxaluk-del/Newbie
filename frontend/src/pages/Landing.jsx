import useReveal from "@/hooks/useReveal";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import Hero from "@/components/sections/Hero";
import Pain from "@/components/sections/Pain";
import Pricing from "@/components/sections/Pricing";
import Process from "@/components/sections/Process";
import FAQ from "@/components/sections/FAQ";
import CTAForm from "@/components/sections/CTAForm";

// Минималистичный лендинг (v4.5): 6 секций вместо 9.
// Удалены ForWhom / Compliance / HowItWorks — их суть осталась
// в Hero / Pricing / Process в виде компактных band'ов.
export default function Landing() {
  const containerRef = useReveal();
  return (
    <div ref={containerRef} data-testid="landing-root">
      <Nav />
      <Hero />
      <hr className="hairline" />
      <Pain />
      <Pricing />
      <Process />
      <FAQ />
      <CTAForm />
      <Footer />
    </div>
  );
}
