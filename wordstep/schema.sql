-- Wordstep user-scoped learning data in Supabase PostgreSQL.
-- Browser may use only the public publishable key; all rows are protected by RLS.
create table if not exists public.wordstep_progress (
  user_id uuid not null references auth.users(id) on delete cascade,
  word_id text not null check (char_length(word_id) between 1 and 80),
  known boolean not null default true,
  updated_at timestamptz not null default now(),
  primary key (user_id,word_id)
);
create table if not exists public.wordstep_preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  constraint wordstep_preferences_payload_is_object check (jsonb_typeof(payload) = 'object')
);
alter table public.wordstep_progress enable row level security;
alter table public.wordstep_preferences enable row level security;
revoke all on public.wordstep_progress, public.wordstep_preferences from public,anon,authenticated;
grant usage on schema public to authenticated;
grant select,insert,update on public.wordstep_progress, public.wordstep_preferences to authenticated;
create policy "Wordstep progress SELECT own" on public.wordstep_progress
  for select to authenticated using ((select auth.uid()) = user_id);
create policy "Wordstep progress INSERT own" on public.wordstep_progress
  for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "Wordstep progress UPDATE own" on public.wordstep_progress
  for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "Wordstep preferences SELECT own" on public.wordstep_preferences
  for select to authenticated using ((select auth.uid()) = user_id);
create policy "Wordstep preferences INSERT own" on public.wordstep_preferences
  for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "Wordstep preferences UPDATE own" on public.wordstep_preferences
  for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
