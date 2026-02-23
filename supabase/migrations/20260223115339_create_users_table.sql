/*
  # Create Users Table

  1. New Tables
    - `users`
      - `id` (uuid, primary key, auto-generated)
      - `username` (text, unique, not null) - unique login identifier
      - `email` (text, unique, not null) - user email address
      - `password_hash` (text, not null) - bcrypt hashed password
      - `first_name` (text, nullable) - user first name
      - `last_name` (text, nullable) - user last name
      - `phone_number` (text, nullable) - optional phone number
      - `is_active` (boolean, default true) - account active status
      - `tradezella_data` (jsonb, nullable) - flexible JSON field for all TradeZella data received via API Gateway
      - `created_at` (timestamptz, default now) - record creation timestamp
      - `updated_at` (timestamptz, default now) - record last update timestamp

  2. Security
    - Enable RLS on `users` table
    - Policy: service role has full access (backend microservice uses service role key)

  3. Notes
    - The tradezella_data JSONB field is intentionally flexible to accommodate any data structure from the TradeZella microservice
    - The admin user row will be inserted/updated by the backend application at startup
    - RLS is enabled but policies allow service_role full access since all access goes through the backend API
*/

CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  username text UNIQUE NOT NULL,
  email text UNIQUE NOT NULL,
  password_hash text NOT NULL,
  first_name text,
  last_name text,
  phone_number text,
  is_active boolean NOT NULL DEFAULT true,
  tradezella_data jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to users"
  ON users
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
