-- PowerForecast Supabase Schema: User Appliances, Usage Sessions Tracking, and Calendar Events
-- Enables multi-source inventory, real-time runtime tracking, and AI-ready metadata

-- 1. USER APPLIANCES TABLE
create table if not exists public.user_appliances (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete cascade not null,
    name text not null,
    category text not null,
    brand text default '',
    model text default '',
    control_no text default '',
    source text default 'manual_entry', -- 'pelp_db' | 'ai_vision' | 'manual_entry' | 'catalog'
    watts numeric not null check (watts > 0),
    voltage numeric default 230,
    quantity integer default 1 check (quantity >= 1),
    hours_per_day numeric not null default 8 check (hours_per_day >= 0 and hours_per_day <= 24),
    days_per_month integer default 30 check (days_per_month >= 1 and days_per_month <= 31),
    monthly_kwh numeric not null default 0,
    estimated_cost numeric default 0,
    energy_rating text default '',
    room_location text default 'General',
    is_active boolean default true,
    is_currently_on boolean default false,
    last_turned_on_at timestamp with time zone,
    ai_metadata jsonb default '{}'::jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 2. APPLIANCE USAGE SESSIONS & RUNTIME LOGS TABLE
create table if not exists public.appliance_usage_logs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete cascade not null,
    appliance_id uuid references public.user_appliances(id) on delete cascade not null,
    started_at timestamp with time zone default timezone('utc'::text, now()) not null,
    ended_at timestamp with time zone, -- Nullable while currently running
    duration_minutes numeric default 0,
    kwh_consumed numeric default 0,
    is_peak_window boolean default false, -- Peak hours (11AM-4PM, 6PM-9PM)
    estimated_cost numeric default 0,
    source text default 'calendar_toggle',
    notes text default '',
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 3. USER CALENDAR UTILITY & APPLIANCE SCHEDULES TABLE
create table if not exists public.user_calendar_events (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id) on delete cascade not null,
    appliance_id uuid references public.user_appliances(id) on delete set null,
    title text not null,
    category text not null default 'appliance', -- 'billing' | 'peak' | 'appliance' | 'audit'
    day text not null default 'mon',
    hour integer not null check (hour >= 0 and hour <= 23),
    duration_hours numeric default 1.0,
    is_recurring boolean default true,
    notes text default '',
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security (RLS)
alter table public.user_appliances enable row level security;
alter table public.appliance_usage_logs enable row level security;
alter table public.user_calendar_events enable row level security;

-- Drop existing policies if any
drop policy if exists "Users can view own appliances" on public.user_appliances;
drop policy if exists "Users can insert own appliances" on public.user_appliances;
drop policy if exists "Users can update own appliances" on public.user_appliances;
drop policy if exists "Users can delete own appliances" on public.user_appliances;

drop policy if exists "Users can view own usage logs" on public.appliance_usage_logs;
drop policy if exists "Users can insert own usage logs" on public.appliance_usage_logs;
drop policy if exists "Users can update own usage logs" on public.appliance_usage_logs;
drop policy if exists "Users can delete own usage logs" on public.appliance_usage_logs;

drop policy if exists "Users can view own calendar events" on public.user_calendar_events;
drop policy if exists "Users can insert own calendar events" on public.user_calendar_events;
drop policy if exists "Users can update own calendar events" on public.user_calendar_events;
drop policy if exists "Users can delete own calendar events" on public.user_calendar_events;

-- RLS Policies for user_appliances
create policy "Users can view own appliances"
    on public.user_appliances for select
    using (auth.uid() = user_id);

create policy "Users can insert own appliances"
    on public.user_appliances for insert
    with check (auth.uid() = user_id);

create policy "Users can update own appliances"
    on public.user_appliances for update
    using (auth.uid() = user_id);

create policy "Users can delete own appliances"
    on public.user_appliances for delete
    using (auth.uid() = user_id);

-- RLS Policies for appliance_usage_logs
create policy "Users can view own usage logs"
    on public.appliance_usage_logs for select
    using (auth.uid() = user_id);

create policy "Users can insert own usage logs"
    on public.appliance_usage_logs for insert
    with check (auth.uid() = user_id);

create policy "Users can update own usage logs"
    on public.appliance_usage_logs for update
    using (auth.uid() = user_id);

create policy "Users can delete own usage logs"
    on public.appliance_usage_logs for delete
    using (auth.uid() = user_id);

-- RLS Policies for user_calendar_events
create policy "Users can view own calendar events"
    on public.user_calendar_events for select
    using (auth.uid() = user_id);

create policy "Users can insert own calendar events"
    on public.user_calendar_events for insert
    with check (auth.uid() = user_id);

create policy "Users can update own calendar events"
    on public.user_calendar_events for update
    using (auth.uid() = user_id);

create policy "Users can delete own calendar events"
    on public.user_calendar_events for delete
    using (auth.uid() = user_id);

-- Grants
grant usage on schema public to postgres, anon, authenticated, service_role;
grant all on table public.user_appliances to postgres, service_role;
grant select, insert, update, delete on table public.user_appliances to authenticated, anon;

grant all on table public.appliance_usage_logs to postgres, service_role;
grant select, insert, update, delete on table public.appliance_usage_logs to authenticated, anon;

grant all on table public.user_calendar_events to postgres, service_role;
grant select, insert, update, delete on table public.user_calendar_events to authenticated, anon;

-- Automatic updated_at trigger function
create or replace function public.handle_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = timezone('utc'::text, now());
    return new;
end;
$$;

drop trigger if exists set_user_appliances_updated_at on public.user_appliances;
create trigger set_user_appliances_updated_at
    before update on public.user_appliances
    for each row execute procedure public.handle_updated_at();

drop trigger if exists set_user_calendar_events_updated_at on public.user_calendar_events;
create trigger set_user_calendar_events_updated_at
    before update on public.user_calendar_events
    for each row execute procedure public.handle_updated_at();
