export const metadata = { title: "ORIOM7 API Documentation", description: "Developer API endpoints, authentication and readiness." };

const endpoints = [
  ["GET", "/v1/developer/products", "List API products and availability."],
  ["POST", "/v1/developer/keys", "Create a developer key; requires trusted sign-in."],
  ["GET", "/v1/developer/keys", "List your key metadata; secrets are never returned."],
  ["DELETE", "/v1/developer/keys/{api_key_id}", "Revoke one of your keys."],
  ["POST", "/v1/embeddings/text", "Generate text embeddings with the configured provider (preview)."],
  ["POST", "/v1/vision/analyze", "Ask a question about a JPEG, PNG or WebP image (provider-configured preview)."],
  ["GET", "/v1/developer/usage", "Read current-month usage using a developer API key."],
];

export default function ApiDocsPage() {
  return <main className="developer-shell">
    <header className="site-header developer-header"><a className="brand" href="/">ORIOM7</a><span className="header-caption">API documentation</span><a className="workspace-link" href="/developer">Developer portal</a></header>
    <section className="developer-hero"><p className="eyebrow">DEVELOPER DOCUMENTATION</p><h1>Integrate ORIOM7.</h1><p>Use the API from your backend. Keep API keys and provider credentials out of browser bundles, public repositories and client-side logs.</p></section>
    <section className="developer-panel developer-section"><h2>Authentication</h2><p>Authenticated API calls use a Bearer token. Session-authenticated key-management endpoints require trusted identity middleware configured by the deployment.</p><pre className="api-code"><code>Authorization: Bearer oriom_live_YOUR_KEY</code></pre></section>
    <section className="developer-section"><div className="developer-section-heading"><div><p className="eyebrow">ENDPOINT REFERENCE</p><h2>Available routes</h2></div><span className="muted">Preview readiness varies by product</span></div>
      <div className="developer-endpoint-list">{endpoints.map(([method, path, description]) => <article className="developer-endpoint" key={path}><span className={`http-method ${method.toLowerCase()}`}>{method}</span><code>{path}</code><p>{description}</p></article>)}</div>
    </section>
    <section className="developer-panel developer-section"><h2>Text embeddings example</h2><p>The embedding endpoint is a preview and requires a configured server-side provider and active ORIOM7 developer API key.</p><pre className="api-code"><code>{`curl -X POST "$ORIOM7_API_URL/v1/embeddings/text" -H "Authorization: Bearer $ORIOM7_API_KEY" -H "Content-Type: application/json" -d '{"input":["A multilingual search engine","Recherche multilingue"]}'`}</code></pre></section>
    <section className="developer-launch-note"><strong>Not yet commercially enabled:</strong> Payments, subscriptions, plan quotas and invoice generation are not configured. Translation, OCR, speech and text-to-speech remain planned catalogue products. Review the <a href="https://github.com/JOHNEBSTER-X7/oriom7-ai-os/blob/feature/oriom7-multidimensional-embeddings/docs/COMMERCIAL_DEVELOPER_API_PLATFORM_V1.md">commercial API implementation notes</a> for production launch gates.</section>
  </main>;
}
