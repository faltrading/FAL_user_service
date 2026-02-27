/*
  # Calendar Availability System - Remove slots, add availability management
  
  ## Changes:
  1. Add `allow_booking_outside_availability` to `calendar_settings`
  2. Create `admin_availability_general` table (weekly schedule, 7 rows)
  3. Create `admin_availability_overrides` table (per-date overrides)
  4. Modify `bookings` table: make slot_id nullable, add direct booking fields
  5. Drop old slot-related indexes
*/

-- 1. Update calendar_settings
ALTER TABLE calendar_settings
  ADD COLUMN IF NOT EXISTS allow_booking_outside_availability boolean NOT NULL DEFAULT false;

-- 2. Create admin_availability_general (one row per day of week)
CREATE TABLE IF NOT EXISTS admin_availability_general (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  day_of_week integer NOT NULL CHECK (day_of_week BETWEEN 0 AND 6), -- 0=Monday, 6=Sunday
  is_enabled boolean NOT NULL DEFAULT true,
  start_time time NOT NULL DEFAULT '08:00',
  end_time time NOT NULL DEFAULT '17:00',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(day_of_week)
);

ALTER TABLE admin_availability_general ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access admin_availability_general"
  ON admin_availability_general
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Seed default availability: Mon-Fri 08:00-17:00, Sat-Sun disabled
INSERT INTO admin_availability_general (day_of_week, is_enabled, start_time, end_time) VALUES
  (0, true,  '08:00', '17:00'),
  (1, true,  '08:00', '17:00'),
  (2, true,  '08:00', '17:00'),
  (3, true,  '08:00', '17:00'),
  (4, true,  '08:00', '17:00'),
  (5, false, '08:00', '17:00'),
  (6, false, '08:00', '17:00')
ON CONFLICT (day_of_week) DO NOTHING;

-- 3. Create admin_availability_overrides (per-date overrides)
CREATE TABLE IF NOT EXISTS admin_availability_overrides (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  override_date date NOT NULL UNIQUE,
  is_closed boolean NOT NULL DEFAULT false,
  start_time time,
  end_time time,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE admin_availability_overrides ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access admin_availability_overrides"
  ON admin_availability_overrides
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- 4. Modify bookings table: make slot_id nullable, add direct booking fields
ALTER TABLE bookings ALTER COLUMN slot_id DROP NOT NULL;

ALTER TABLE bookings
  ADD COLUMN IF NOT EXISTS booking_date date,
  ADD COLUMN IF NOT EXISTS start_time time,
  ADD COLUMN IF NOT EXISTS end_time time;

-- Drop old unique constraint (one confirmed booking per slot)
DROP INDEX IF EXISTS idx_bookings_one_confirmed_per_slot;

-- Create new index: prevent overlapping confirmed bookings on same date
CREATE INDEX IF NOT EXISTS idx_bookings_date_status
  ON bookings(booking_date, status) WHERE status = 'confirmed';
