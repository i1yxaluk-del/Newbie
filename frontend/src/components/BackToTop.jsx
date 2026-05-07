import { useEffect, useState } from "react";

export default function BackToTop() {
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const onScroll = () => setShown(window.scrollY > 600);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handle = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <button
      type="button"
      onClick={handle}
      data-testid="back-to-top"
      aria-label="Наверх"
      title="Наверх"
      style={{
        position: "fixed",
        right: 24,
        bottom: 24,
        width: 48,
        height: 48,
        borderRadius: 999,
        background: "#0e0c0a",
        color: "#f5f1e8",
        border: "1px solid rgba(255,255,255,.10)",
        boxShadow: "0 8px 24px rgba(0,0,0,.18)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
        opacity: shown ? 1 : 0,
        transform: shown ? "translateY(0)" : "translateY(12px)",
        pointerEvents: shown ? "auto" : "none",
        transition: "opacity .2s ease, transform .2s ease",
        zIndex: 90,
        padding: 0,
      }}
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M12 19V5" />
        <path d="M5 12l7-7 7 7" />
      </svg>
    </button>
  );
}
