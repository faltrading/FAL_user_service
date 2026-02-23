/*
  # Create Payment Plans Table

  1. New Tables
    - `payment_plans`
      - `id` (uuid, primary key)
      - `name` (text, not null) - plan name (e.g. "Basic", "Pro", "Enterprise")
      - `description` (text, nullable) - plan description
      - `price_cents` (integer, not null) - price in cents to avoid floating point issues
      - `currency` (text, default EUR) - currency code
      - `billing_interval` (text) - billing cycle: monthly, yearly, or one_time
      - `features` (jsonb, nullable) - list of features included in the plan
      - `is_active` (boolean, default true) - whether the plan is currently offered
      - `created_at` (timestamptz)
      - `updated_at` (timestamptz)

  2. Security
    - Enable RLS on `payment_plans` table
    - Service role has full access
*/

CREATE TABLE IF NOT EXISTS payment_plans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text,
  price_cents integer NOT NULL DEFAULT 0,
  currency text NOT NULL DEFAULT 'EUR',
  billing_interval text NOT NULL DEFAULT 'monthly' CHECK (billing_interval IN ('monthly', 'yearly', 'one_time')),
  features jsonb,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE payment_plans ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to payment_plans"
  ON payment_plans
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
