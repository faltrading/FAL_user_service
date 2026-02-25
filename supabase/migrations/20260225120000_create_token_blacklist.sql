/*
  # Token Blacklist Table (for logout / session revocation)
  
  Stores SHA-256 hashes of revoked JWT tokens.
  Tokens are automatically cleaned up after expiration.
*/

CREATE TABLE IF NOT EXISTS token_blacklist (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  token_hash text UNIQUE NOT NULL,
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_token_blacklist_hash ON token_blacklist(token_hash);
CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires ON token_blacklist(expires_at);

ALTER TABLE token_blacklist ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access to token_blacklist"
  ON token_blacklist FOR ALL TO service_role USING (true) WITH CHECK (true);
