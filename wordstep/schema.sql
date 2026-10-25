-- Wordstep: cloud study progress with user-isolated access.
-- Run once in your own Supabase project's SQL editor.
-- Never put a service_role or secret key in the browser.
create table if not exists public.wordstep_progress (
  user_id uuid not null references auth.users(id) on delete cascade,
  word_id text not null check (length(word_id) between 1 and 80),
  known boolean not null default true,
  updated_at timestamptz not null default now(),
  primary key (user_id, word_id)
);

create table if not exists public.wordstep_preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  constraint wordstep_prefs_object check (jsonb_typeof(payload) = 'object')
);

alter table public.wordstep_progress enable row level security;
alter table public.wordstep_preferences enable row level security;

-- RLS policies are idempotent to support safe re-runs.
drop policy if exists "Read own Wordstep progress" on public.wordstep_progress;
drop policy if exists "Insert own Wordstep progress" on public.wordstep_progress;
drop policy if exists "Update own Wordstep progress" on public.wordstep_progress;
drop policy if exists "Read own Wordstep preferences" on public.wordstep_preferences;
drop policy if exists "Insert own Wordstep preferences" on public.wordstep_preferences;
drop policy if exists "Update own Wordstep preferences" on public.wordstep_preferences;

create policy "Read own Wordstep progress" on public.wordstep_progress
  for select to authenticated using ((select auth.uid()) = user_id);
create policy "Insert own Wordstep progress" on public.wordstep_progress
  for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "Update own Wordstep progress" on public.wordstep_progress
  for update to authenticated using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "Read own Wordstep preferences" on public.wordstep_preferences
  for select to authenticated using ((select auth.uid()) = user_id);
create policy "Insert own Wordstep preferences" on public.wordstep_preferences
  for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "Update own Wordstep preferences" on public.wordstep_preferences
  for update to authenticated using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

revoke all on public.wordstep_progress, public.wordstep_preferences from anon;
grant select, insert, update on public.wordstep_progress, public.wordstep_preferences to authenticated;
