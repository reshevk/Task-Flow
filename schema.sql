-- Run this once in Supabase: SQL Editor -> New query -> Run
create table if not exists public.tasks (
  id          uuid primary key default gen_random_uuid(),
  title       text not null check (char_length(title) between 1 and 200),
  done        boolean not null default false,
  priority    text not null default 'medium' check (priority in ('high', 'medium', 'low')),
  due_date    date,
  created_at  timestamptz not null default now()
);

-- The backend uses the service_role key, which bypasses RLS.
-- Enabling RLS with no policies blocks anyone using the public anon key.
alter table public.tasks enable row level security;
