# Wordstep: cloud data setup

This upgrade preserves the current 1,969 word cards and the existing UI. Learning progress still saves to localStorage immediately, and syncs to Supabase after email sign-in. Manual JSON export/import remains available even when offline.

## One-time Supabase setup

1. Create/select a Supabase project and execute `schema.sql` in its SQL editor.
2. In **Authentication > URL Configuration**, set Site URL to `https://jay940106happy.github.io/test/wordstep/` and add the same URL to **Redirect URLs**.
3. Enable **Email** sign-in (OTP magic links) and confirm the project's mail sender/rate limits.
4. Add your project's URL and **publishable/anon** key to `wordstep/cloud-config.json`, then commit. **Never use the service-role key.** The key is exposed by design; RLS policies restrict private rows.
5. Check sign-in and learning state from two browsers/devices. The logged-in user should see the same progress.

The Supabase DB is provisioned only when these steps are actually executed against your project; publishing this source alone does not create it.

## Previously learned words

The original Wordstep used browser-local storage, so progress cannot automatically cross `raw.githack.com` to `github.io`. Export a backup in the old browser when available, then import in the new site and sign in to upload it. `Wordstep` backups contain `known` word IDs and basic learning preferences.

## Deployment

The current site is served from `test/wordstep/` on GitHub Pages. Cloud configuration is public and non-secret; the database schema and auth settings are the security boundary.
