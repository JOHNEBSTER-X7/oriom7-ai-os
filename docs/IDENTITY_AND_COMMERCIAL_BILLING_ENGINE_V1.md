# ORIOM7 Identity and Commercial Billing Engine V1

This milestone establishes authenticated account profiles, organisation membership, plan catalogue, subscription and invoice read models, and monthly usage summaries.

Private routes reuse the existing authenticated_subject dependency and require deployment-managed trusted identity middleware. No passwords, homemade sessions, or unverified identity headers are introduced.

Payment collection remains disabled. Paid plan prices remain unset pending commercial approval. Checkout, signed payment webhooks, refunds, tax calculation and subscription changes are not active.

Usage-ledger schema is a foundation and is not yet connected to API-key metering or atomic quota enforcement.

Production gates: configure a managed OIDC/session provider; verify issuer, audience, signature, expiry and key rotation; select a payment provider; implement signed and idempotent webhooks; connect metering and quota enforcement; rehearse migrations and complete security review.