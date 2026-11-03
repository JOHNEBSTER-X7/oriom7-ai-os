import ResearchWorkspace from "../../components/ResearchWorkspace";

export default function ResearchPage() {
  return (
    <>
      <a className="skip-link" href="#research-main">Skip to research workspace</a>
      <main id="research-main" className="research-shell">
        <header className="site-header">
          <a className="brand" href="/" aria-label="ORIOM7 home">ORIOM7</a>
          <span className="header-caption">Research intelligence</span>
          <a className="workspace-link" href="/research/review">Evidence review centre</a>
          <a className="workspace-link" href="/">Accessibility settings</a>
        </header>
        <ResearchWorkspace />
      </main>
    </>
  );
}
