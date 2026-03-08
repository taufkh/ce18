# TH Account Statement Changelog

This file is the single source of truth for module-level change tracking.
Every functional change, bug fix, UI update, and deployment-impacting update
must add one entry here.

## Entry Format

- Date (`YYYY-MM-DD`)
- Type (`FIX`, `FEAT`, `CHORE`, `SEC`)
- Scope (file/feature area)
- Summary (what changed)
- Impact (what user behavior changes)
- Commit hash

## 2026-03-08

### [FIX] Portal download wizard required date fields
- Scope: portal controller download endpoints
- Summary:
  - Ensure wizard date range is always populated for portal/shared downloads.
  - Fix PDF rendering call to pass correct `report_name` and `res_ids`.
- Impact:
  - Portal buttons `View/Download Statement` and `View/Download Overdue` no longer fail with mandatory `date_from` error.
  - PDF and XLS endpoints return successful responses.
- Commit: `d0a7b2b`

### [FIX] Portal download robustness (initial pass)
- Scope: portal controller wizard builder
- Summary:
  - Add fallback date resolution in wizard builder for non-filtered portal downloads.
- Impact:
  - Prevents empty date payload from creating invalid wizard records.
- Commit: `b976e58`

## 2026-03-07

### [FIX] Overview Owl lifecycle error in Statement History
- Scope: overview form list view
- Summary:
  - Stabilize list rendering to avoid aggregate crashes in Owl ListRenderer.
  - Remove problematic monetary aggregate usage in transient list lines.
- Impact:
  - Opening Statement History records no longer triggers `Cannot read properties of undefined (reading '0')`.
- Commit: `29b6fbf`

### [FEAT] Shareable portal statement URL from partner form
- Scope: partner model, partner form view, portal controller/template
- Summary:
  - Add `statement_share_token` and computed `statement_share_url`.
  - Add `Generate Share URL` and `Open Share URL` buttons in partner statement tab.
  - Add public token-based shared statement page and download endpoints.
- Impact:
  - Internal user can generate/share statement link directly from partner form.
  - Recipient can open statement page and download PDF/XLS via tokenized URL.
- Commit: `29b6fbf`

### [FEAT] Shared portal UI redesign
- Scope: shared portal template
- Summary:
  - Replace plain output with structured card/table layout.
  - Add KPI summary, styled section headers, and mobile-friendly behavior.
  - Format date and monetary values for readability.
- Impact:
  - Shared portal page is now presentation-ready and consistent with report style.
- Commit: `29b6fbf`

### [FIX] Multi-database safe share URL
- Scope: partner URL generation logic
- Summary:
  - Generate share URL through `/web/login?db=<db>&redirect=<share-path>` to enforce DB context.
- Impact:
  - Shared links open reliably in multi-DB setup without random `404` caused by missing DB context.
- Commit: `d42ffc6`

## Changelog Discipline

For every future change in `th_account_statement`:

1. Add/update tests when applicable.
2. Add one concise changelog entry in this file.
3. Include commit hash after push.
4. Mention migration/deploy impact if any (module upgrade, restart, data backfill).

