/*
  # Create Bookings Table

  1. New Tables
    - `bookings`
      - `id` (uuid, primary key)
      - `slot_id` (uuid, FK to calendar_slots, not null) - the booked slot
      - `user_id` (uuid, FK to users, not null) - the user who booked
      - `status` (text, default 'confirmed') - booking status: confirmed or cancelled
      - `cancelled_at` (timestamptz, nullable) - when the booking was cancelled
      - `notes` (text, nullable) - user notes about the booking
      - `created_at` (timestamptz)
      - `updated_at` (timestamptz)

  2. Security
    - Enable RLS on `bookings` table
    - Service role has full access

  3. Indexes
    - Index on user_id for fast user booking lookups
    - Index on slot_id for fast slot availability checks
    - Unique partial index: only one confirmed booking per slot
*/

CREATE TABLE IF NOT EXISTS bookings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slot_id uuid NOT NULL REFERENCES calendar_slots(id),
  user_id uuid NOT NULL REFERENCES users(id),
  status text NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'cancelled')),
  cancelled_at timestamptz,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_slot_id ON bookings(slot_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_bookings_one_confirmed_per_slot
  ON bookings(slot_id) WHERE status = 'confirmed';

ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to bookings"
  ON bookings
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
