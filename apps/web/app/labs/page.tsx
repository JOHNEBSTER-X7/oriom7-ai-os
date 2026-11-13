import LabWorkspace from "../../components/LabWorkspace";

export default function LabsPage() {
  return (
    <>
      <a className="skip-link" href="#labs-main">Skip to laboratory workspace</a>
      <main id="labs-main" className="research-shell">
        <header className="site-header">
          <a className="brand" href="/" aria-label="ORIOM7 home">ORIOM7</a>
          <span className="header-caption">LAB OS</span>
          <a className="workspace-link" href="/research">Research intelligence</a>
          <a className="workspace-link" href="/">Home</a>
        </header>
        <LabWorkspace />
      </main>
    </>
  );
}
