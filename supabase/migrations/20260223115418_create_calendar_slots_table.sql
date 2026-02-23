/*
  # Create Calendar Slots Table

  1. New Tables
    - `calendar_slots`
      - `id` (uuid, primary key)
      - `date` (date, not null) - the date of the slot
      - `start_time` (timestamptz, not null) - slot start datetime
      - `end_time` (timestamptz, not null) - slot end datetime
      - `is_available` (boolean, default true) - whether the slot is open for booking
      - `notes` (text, nullable) - admin notes about the slot
      - `created_by` (uuid, FK to users) - admin who created the slot
      - `created_at` (timestamptz)
      - `updated_at` (timestamptz)

  2. Security
    - Enable RLS on `calendar_slots` table
    - Service role has full access

  3. Indexes
    - Index on date for fast date-range queries
    - Index on is_available for filtering available slots
*/

CREATE TABLE IF NOT EXISTS calendar_slots (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  date date NOT NULL,
  start_time timestamptz NOT NULL,
  end_time timestamptz NOT NULL,
  is_available boolean NOT NULL DEFAULT true,
  notes text,
  created_by uuid REFERENCES users(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT valid_time_range CHECK (end_time > start_time)
);

CREATE INDEX IF NOT EXISTS idx_calendar_slots_date ON calendar_slots(date);
CREATE INDEX IF NOT EXISTS idx_calendar_slots_available ON calendar_slots(is_available);

ALTER TABLE calendar_slots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to calendar_slots"
  ON calendar_slots
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
