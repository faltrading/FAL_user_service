/*
  # Create User Payments Table

  1. New Tables
    - `user_payments`
      - `id` (uuid, primary key)
      - `user_id` (uuid, FK to users, not null) - the paying user
      - `plan_id` (uuid, FK to payment_plans, nullable) - associated plan
      - `status` (text) - payment status: pending, active, expired, cancelled, failed
      - `payment_provider` (text, nullable) - provider name for future integration (e.g. stripe, paypal)
      - `external_payment_id` (text, nullable) - transaction ID from external provider
      - `amount_cents` (integer, nullable) - actual amount charged
      - `currency` (text, default EUR)
      - `started_at` (timestamptz, nullable) - subscription start
      - `expires_at` (timestamptz, nullable) - subscription expiration
      - `cancelled_at` (timestamptz, nullable) - when cancelled
      - `metadata` (jsonb, nullable) - extra data from payment provider
      - `created_at` (timestamptz)
      - `updated_at` (timestamptz)

  2. Security
    - Enable RLS on `user_payments` table
    - Service role has full access

  3. Indexes
    - Index on user_id for fast lookups
    - Index on status for filtering
*/

CREATE TABLE IF NOT EXISTS user_payments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id),
  plan_id uuid REFERENCES payment_plans(id),
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'expired', 'cancelled', 'failed')),
  payment_provider text,
  external_payment_id text,
  amount_cents integer,
  currency text NOT NULL DEFAULT 'EUR',
  started_at timestamptz,
  expires_at timestamptz,
  cancelled_at timestamptz,
  metadata jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_payments_user_id ON user_payments(user_id);
CREATE INDEX IF NOT EXISTS idx_user_payments_status ON user_payments(status);

ALTER TABLE user_payments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to user_payments"
  ON user_payments
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
