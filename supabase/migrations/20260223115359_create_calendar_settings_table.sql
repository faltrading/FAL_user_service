/*
  # Create Calendar Settings Table

  1. New Tables
    - `calendar_settings`
      - `id` (uuid, primary key) - single row expected (global settings)
      - `slot_duration_minutes` (integer, nullable) - null means no fixed slot duration
      - `default_start_time` (time) - daily availability start (e.g. 08:00)
      - `default_end_time` (time) - daily availability end (e.g. 17:00)
      - `timezone` (text, default UTC) - calendar timezone
      - `min_booking_notice_minutes` (integer, nullable) - minimum advance notice to book
      - `max_advance_booking_days` (integer, nullable) - how far in advance users can book
      - `allow_cancellation` (boolean, default true) - whether users can cancel bookings
      - `cancellation_notice_minutes` (integer, nullable) - minimum notice to cancel
      - `created_at` (timestamptz)
      - `updated_at` (timestamptz)

  2. Security
    - Enable RLS on `calendar_settings` table
    - Service role has full access (backend manages all calendar logic)
*/

CREATE TABLE IF NOT EXISTS calendar_settings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slot_duration_minutes integer,
  default_start_time time NOT NULL DEFAULT '08:00',
  default_end_time time NOT NULL DEFAULT '17:00',
  timezone text NOT NULL DEFAULT 'UTC',
  min_booking_notice_minutes integer,
  max_advance_booking_days integer,
  allow_cancellation boolean NOT NULL DEFAULT true,
  cancellation_notice_minutes integer,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE calendar_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role has full access to calendar_settings"
  ON calendar_settings
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
