-- PowerForecast Supabase Accounts Schema
-- Strictly for User Accounts Management

-- 1. Accounts Table
create table if not exists public.accounts (
    id uuid references auth.users(id) on delete cascade primary key,
    full_name text,
    email text unique,
    avatar_url text,
    provider text default 'email',
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

alter table public.accounts enable row level security;

-- Drop existing policies if any
drop policy if exists "Users can view own account" on public.accounts;
drop policy if exists "Users can update own account" on public.accounts;
drop policy if exists "Users can insert own account" on public.accounts;

-- RLS Policies for Accounts
create policy "Users can view own account"
    on public.accounts for select
    using (auth.uid() = id);

create policy "Users can update own account"
    on public.accounts for update
    using (auth.uid() = id);

create policy "Users can insert own account"
    on public.accounts for insert
    with check (auth.uid() = id);

-- Grant appropriate permissions
grant usage on schema public to postgres, anon, authenticated, service_role;
grant all on table public.accounts to postgres, service_role;
grant select, insert, update on table public.accounts to authenticated, anon;

-- 2. Automatic Trigger to Sync auth.users on signup
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public, auth
as $$
begin
    insert into public.accounts (id, full_name, email, avatar_url, provider)
    values (
        new.id,
        coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', ''),
        new.email,
        coalesce(new.raw_user_meta_data->>'avatar_url', new.raw_user_meta_data->>'picture', ''),
        coalesce(new.raw_app_meta_data->>'provider', 'email')
    )
    on conflict (id) do update set
        full_name = coalesce(excluded.full_name, accounts.full_name),
        email = coalesce(excluded.email, accounts.email),
        avatar_url = coalesce(excluded.avatar_url, accounts.avatar_url),
        updated_at = now();
    return new;
exception
    when others then
        return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute procedure public.handle_new_user();
