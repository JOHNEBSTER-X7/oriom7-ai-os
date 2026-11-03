import EvidenceReviewCentre from "../../../components/EvidenceReviewCentre";

export default function EvidenceReviewPage() {
  return (
    <>
      <a className="skip-link" href="#verification-main">Skip to evidence review queue</a>
      <main id="verification-main" className="verification-shell">
        <header className="site-header">
          <a className="brand" href="/" aria-label="ORIOM7 home">ORIOM7</a>
          <span className="header-caption">Evidence verification</span>
          <nav className="verification-nav" aria-label="Workspace navigation">
            <a href="/research">Research workspace</a>
            <a href="/">Accessibility settings</a>
          </nav>
        </header>
        <EvidenceReviewCentre />
      </main>
    </>
  );
}
