# Wordstep — personal TOEIC learning with cloud sync

Public site: https://jay940106happy.github.io/test/wordstep/

- 1,969 distinct vocabulary cards, 3,938 bilingual example sentences and categorized learning modes.
- Wordstep preserves the existing localStorage keys `wordstep.progress.v1` and `wordstep.preferences.v1`.
- Authentication: Supabase Auth email/password. Click **學習紀錄 / 登入** and create an account or log in.
- Sync: read/merge cloud state on sign-in and when the site regains focus; local edits save immediately and sync after sign-in.
- Backup/restore JSON works offline, and imported progress is uploaded after sign-in.
- Supabase project: `wordstep-study` (Tokyo). Database tables `public.wordstep_progress`, `public.wordstep_preferences`; RLS owner-only policies are enabled. The public publishable key is intentionally readable in `cloud-config.json`. Never use a service-role/secret key in this site.
- The email/password signup flow may require email confirmation. A Supabase dashboard owner should set **Authentication → URL Configuration**: Site URL and Redirect URLs to `https://jay940106happy.github.io/test/wordstep/`. This administrative setting is not accessible through the currently connected automation API. Confirmation can still verify an account even if the default redirect is not set; return to the Wordstep URL and log in after clicking the confirmation link.
- Supabase's default SMTP can deliver only to pre-authorized project-team addresses. To open signups to other people, configure a custom SMTP provider in the dashboard.
- No user's progress was uploaded from their old GitHack browser; browser storage is origin-isolated. Use the JSON backup import if the old device is available.

Content attribution: Original David TOEIC list and TSL 1.2 (Browne & Culligan); bilingual examples partly from kknono668/toeic-vocab-tw (CC BY-SA 4.0), with independently authored additions.

## Smoke checks

1. Confirm the public HTML contains exactly 1,969 cards and 3,938 examples.
2. Visit **學習紀錄 / 登入**, register and verify email, then log in.
3. Mark a word and observe **雲端同步成功** or **已同步到雲端**.
4. Sign in on another device and compare word status. Use **立即同步** to refresh.
5. Export/import JSON backup. Signing out keeps remote records; logged-in records are partitioned by Supabase user ID.
