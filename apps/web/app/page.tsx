import AccessibilitySettings from "../components/AccessibilitySettings";

export default function HomePage() {
  return (
    <main id="main-content" className="page-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="site-header">
        <a className="brand" href="/" aria-label="ORIOM7 home">ORIOM7</a>
        <span className="header-caption">Universal AI search</span>
      </header>
      <section className="intro">
        <p className="eyebrow">ORIOM7 · ACCESSIBILITY</p>
        <h1>Make ORIOM7 work the way you need.</h1>
        <p>Choose the display, reading and interaction settings that make searching more comfortable. You do not need to tell us about a diagnosis.</p>
      </section>
      <AccessibilitySettings />
    </main>
  );
}
