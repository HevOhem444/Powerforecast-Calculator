-- Migration: Allow decimal/fractional hours for sub-hour precision in calendar events
-- Date: 2026-08-19

ALTER TABLE public.user_calendar_events 
    DROP CONSTRAINT IF EXISTS user_calendar_events_hour_check;

ALTER TABLE public.user_calendar_events 
    ALTER COLUMN hour TYPE numeric USING hour::numeric;

ALTER TABLE public.user_calendar_events 
    ADD CONSTRAINT user_calendar_events_hour_check 
    CHECK (hour >= 0 AND hour < 24);

-- Indexes for lightning-fast cross-device queries
CREATE INDEX IF NOT EXISTS idx_user_calendar_events_user_day 
    ON public.user_calendar_events(user_id, day);

CREATE INDEX IF NOT EXISTS idx_user_calendar_events_appliance 
    ON public.user_calendar_events(appliance_id);
