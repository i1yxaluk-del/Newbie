import useReveal from "@/hooks/useReveal";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";
import Hero from "@/components/sections/Hero";
import Pain from "@/components/sections/Pain";
import HowItWorks from "@/components/sections/HowItWorks";
import ForWhom from "@/components/sections/ForWhom";
import Compliance from "@/components/sections/Compliance";
import Compare from "@/components/sections/Compare";
import Pricing from "@/components/sections/Pricing";
import Process from "@/components/sections/Process";
import Tools from "@/components/sections/Tools";
import Cases from "@/components/sections/Cases";
import FAQ from "@/components/sections/FAQ";
import CTAForm from "@/components/sections/CTAForm";

export default function Landing() {
  const containerRef = useReveal();
  return (
    <div ref={containerRef} data-testid="landing-root">
      <Nav />
      <Hero />
      <hr className="hairline" />
      <Pain />
      <HowItWorks />
      <ForWhom />
      <Compliance />
      <Compare />
      <Pricing />
      <Process />
      <Tools />
      <Cases />
      <FAQ />
      <CTAForm />
      <Footer />
    </div>
  );
}
