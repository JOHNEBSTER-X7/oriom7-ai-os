# ORIOM7 Identity, Organisation and Commercial Billing V1

## Delivered

### Managed OIDC sign-in
- Next.js authorization-code flow with PKCE S256, random state and nonce.
- Callback exchanges the authorization code server-side.
- ID token is verified for signature, issuer, client audience and nonce.
- API access token is verified for signature, issuer and configured API audience before it is accepted.
- Access token is stored in an HttpOnly, SameSite=Lax cookie; Next.js server routes pass it to FastAPI as a Bearer token.
- API middleware verifies RS256 JWTs against a cached JWKS set and refreshes keys when an unknown key ID is seen.
- Email verification and account recovery are delegated to the selected identity provider. Organisation invitation acceptance requires an `email_verified=true` claim.

This is a generic OIDC integration, not a bundled identity provider. No provider tenant, client secret or production credentials are included.

### Organisations and roles
- Create and list organisations; creator receives owner role.
- Admins/owners can create seven-day invitations for verified email addresses.
- Invitation tokens are random, stored only as SHA-256 hashes and displayed once.
- Invitees must authenticate with the matching verified email address to accept.
- Members can be listed; owners can update non-owner roles and remove non-owner members.
- Roles: owner, admin, developer, billing_viewer. Owner role cannot be reassigned through the member role endpoint.
- Invitation email delivery is not integrated yet. The API returns a one-time token for secure manual delivery; configure a transactional email provider before broad production use.

### Stripe subscriptions
- Checkout Session creation for Builder and Business monthly plans.
- Stripe customer IDs are associated with ORIOM7 accounts.
- Checkout is disabled unless the Stripe secret key, webhook signing secret, configured Price ID and trusted success/cancel URLs are present.
- Webhook signatures are verified using timestamped HMAC-SHA256 with a five-minute tolerance.
- Events are idempotently recorded; only a minimal, allow-listed event payload is stored.
- Checkout completion and subscription lifecycle events update subscription state.
- Invoice finalization, payment, failure and void events update invoice read models.
- Checkout URLs are returned to the browser; card data is never handled by ORIOM7.

No live Stripe account or keys are configured in this repository. Use Stripe test mode first.

### Usage metering and quotas
- Every authenticated developer API-key request is recorded as an internal request event.
- Monthly quota is calculated across all keys owned by the account.
- PostgreSQL advisory transaction locks serialize quota checks per account, preventing concurrent requests from racing past the monthly request allowance.
- Effective plan comes from the active/trialing subscription, not the API-key creation request.
- Starter is the default entitlement. Paid entitlements become effective only after a verified Stripe subscription webhook.
- Product-specific units (such as embedding input characters) remain separately recorded.

## Database migrations

Apply migrations 001–015 in order, including:
- 013 account, organisation, plan, subscription, invoice, payment-event and usage-ledger foundations.
- 014 Stripe customer mapping and idempotency/index support.
- 015 organisation invitations.

Back up PostgreSQL and rehearse migrations before production. Do not assume an existing deployment has applied them.

## Required environment configuration

### FastAPI service
- `DATABASE_URL`
- `ORIOM7_OIDC_ISSUER`
- `ORIOM7_OIDC_AUDIENCE` (API resource audience)
- `ORIOM7_OIDC_JWKS_URL`
- `ORIOM7_OIDC_CLIENT_ID`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `ORIOM7_STRIPE_PRICE_BUILDER_MONTHLY`
- `ORIOM7_STRIPE_PRICE_BUSINESS_MONTHLY`
- `ORIOM7_BILLING_SUCCESS_URL`
- `ORIOM7_BILLING_CANCEL_URL`

### Next.js web service
- `ORIOM7_API_URL`
- `ORIOM7_OIDC_AUTHORIZATION_ENDPOINT`
- `ORIOM7_OIDC_TOKEN_ENDPOINT`
- `ORIOM7_OIDC_ISSUER`
- `ORIOM7_OIDC_JWKS_URL`
- `ORIOM7_OIDC_CLIENT_ID`
- `ORIOM7_OIDC_CLIENT_SECRET`
- `ORIOM7_OIDC_AUDIENCE`
- `ORIOM7_OIDC_REDIRECT_URI` (must exactly match the identity-provider callback URL)
- `ORIOM7_OIDC_SCOPES`

The OIDC provider must issue RS256-signed JWT access tokens whose issuer, JWKS and API audience match the FastAPI configuration. The confidential web client must permit the authorization-code flow and PKCE S256. The verified ID token is passed server-to-server in addition to the access token so FastAPI can validate the same subject and trusted email-verification claim. The client secret is server-only.

## Production launch gates
1. Select a managed OIDC provider and configure its confidential web client and API audience.
2. Confirm the provider issues RS256 JWT access tokens with the configured issuer and audience; test key rotation and token expiry.
3. Configure verified email claims and account recovery in the provider.
4. Configure Stripe test-mode product prices and webhook endpoint; test checkout, duplicate events, cancellations, failed payments and invoice lifecycle.
5. Configure a transactional email service for invitation delivery; invitation tokens must be delivered privately and never logged.
6. Apply migrations 001–015 to a staging PostgreSQL database and run end-to-end tests.
7. Complete security, privacy, tax, consumer terms, refunds, cancellation and operational support reviews before live payments.
8. Review npm audit findings and pin/lock dependency versions before production.

## Explicit limitations
- This code does not create or configure a third-party OIDC tenant, Stripe account, products, prices or webhook endpoint.
- No credentials, customer payments or real subscriptions are active until operators configure the above environment.
- No tax calculation, refunds, charge disputes, dunning emails, customer portal, automatic invoice PDF generation or subscription cancellation UI is implemented.
- Invitation tokens are created, hashed and validated, but automatic invitation email delivery is not implemented.
- Usage quota is a monthly request-count allowance. It is not yet a per-product monetary cost budget.
- Enterprise plan requires manual commercial contracting.
