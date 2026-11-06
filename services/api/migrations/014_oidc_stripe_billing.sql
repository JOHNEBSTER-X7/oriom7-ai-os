-- ORIOM7 managed identity and Stripe billing integration.
ALTER TABLE oriom7_accounts ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS oriom7_accounts_stripe_customer_idx
 ON oriom7_accounts(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS oriom7_subscriptions_provider_id_idx
 ON oriom7_subscriptions(provider,provider_subscription_id)
 WHERE provider_subscription_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS oriom7_payment_events_unprocessed_idx
 ON oriom7_payment_events(received_at) WHERE processed_at IS NULL;
