# WF-14: Status

**Date**: 2026-09-05
**Ceremony**: large
**FRs**: FR-PROJECT-001, FR-CREATE-001, FR-SHEET-001, FR-SYNC-001, FR-SYNC-RATES-001, FR-PAYMENT-001

## History

| # | Plan | Tasks | Date | Outcome |
|---|------|-------|------|---------|
| 1 | [plan-001.md](archive/plan-001.md) | [tasks-001.md](archive/tasks-001.md) | 2026-09-05 | implemented |
| 001 | [plan-001.md](archive/plan-001.md) | [tasks-001.md](archive/tasks-001.md) | 2026-09-05 | Implemented |
| 2 | [plan-002.md](archive/plan-002.md) | [tasks-002.md](archive/tasks-002.md) | 2026-09-05 | implemented — Next.js rewrite keeps card GET trailing slash |
| 002 | [plan-002.md](archive/plan-002.md) | [tasks-002.md](archive/tasks-002.md) | 2026-09-05 | Implemented |
| 003 | [plan-003.md](archive/plan-003.md) | [tasks-003.md](archive/tasks-003.md) | 2026-09-05 | Implemented |
| 004 | [plan-004.md](archive/plan-004.md) | [tasks-004.md](archive/tasks-004.md) | 2026-09-05 | Implemented — `window.open('')` + `document.write`; address bar stayed `about:blank` |
| 005 | [plan-005.md](archive/plan-005.md) | [tasks-005.md](archive/tasks-005.md) | 2026-09-05 | Implemented |

## Plan summary

Cycle 5 (planned): stop `window.open('')` / `document.write`. Add `feptm-web/public/creating.html` titled `Creating...`. `CreateProjectOverlay` `handleSubmit` opens `window.open` of that same-origin href with no features and passes `Window` into `useCreateProject`. Keep Cycle 4 handoff: on success `location.replace` the card href, then close overlay; if replace throws, close the tab and fallback `window.open(href, '_blank', 'noopener,noreferrer')`. On error close the placeholder tab. Do not change `useCreateProject.ts`, list `Link`, card heading, command-row buttons, feptm-server, or `next.config.ts`.

Cycle 4 (done): stop `window.open('about:blank')`. `CreateProjectOverlay` `handleSubmit` opens `window.open('', '_blank')` with no features, writes a same-origin `Creating...` document, passes `Window` into `useCreateProject`. On success `location.replace` the card href, then close overlay; if replace throws, close the tab and fallback `window.open(href, '_blank', 'noopener,noreferrer')`. On error close the placeholder tab. Chrome and Yandex still show `about:blank` in the address bar.

Cycle 3 (done): open the card in a new browser tab on project-name click (`Link` `target="_blank"`) and after successful create (placeholder `about:blank` tab, then `location.replace`). Dashboard list stays in the previous tab. Heading word `Project` uses `--accent`; project name keeps `--foreground`. Update rates and Close period in the command row use `PrimaryButton`. Close period modal Confirm stays primary, Cancel stays secondary. feptm-server, `next.config.ts`, API client, FR-THEME-001 out of scope.

Cycle 2 (done): add one rewrite in `feptm-web/next.config.ts`: `/api/projects/:driveFolderId/` → `{apiOrigin}/api/projects/:driveFolderId/`, after the list rules and before `/api/:path*`. Catch-all drops the slash; FastAPI 307 to `:8000` breaks card load (CORS). Do not change feptm-server, API client, or UI copy. Do not add a no-slash `:driveFolderId` rule (would match create/sync/sync-rates).

Cycle 1 (done): same-tab project card at `/projects/{drive_folder_id}`. Create overlay calls `POST /api/projects/create` and navigates to the card. Card loads `GET /api/projects/{drive_folder_id}/`, shows ForEach Partners header, `Project {name}`, Update team / Update rates / Close period, and Tables links. Mutations use `project_id` from the card. feptm-server unchanged. FR-THEME-001 out of scope.

## Baseline audit

- Policy: `fix_err`
- web: 0 ERR, 1 WARN (`.gitignore` missing `.DS_Store`)
- No ERR remediation in this workflow

## Implementation

Cycle 5: 3/3 tasks done.

| Task | Status | Note |
|------|--------|------|
| T-01 | done | static `public/creating.html` |
| T-02 | done | `window.open` `/creating.html` |
| T-03 | done | Audit touched files |

## Progress

- 2026-09-05T19:55 cycle 5 implement complete: 3/3 done, 0 blocked
- 2026-09-05T19:55 T-03 done — audit touched files: 0 ERR, 0 WARN; baseline WARN `.DS_Store` unchanged
- 2026-09-05T19:54 T-02 done — `window.open` `/creating.html`; verify implement OK
- 2026-09-05T19:53 T-01 done — static `public/creating.html`; verify implement OK
- 2026-09-05T19:51 plan.md and tasks.md written (cycle 5)
- 2026-09-05T19:26 cycle 4 implement complete: 3/3 done, 0 blocked
- 2026-09-05T19:26 T-03 done — audit touched files: 0 ERR, 0 WARN; baseline WARN `.DS_Store` unchanged
- 2026-09-05T19:21 T-02 done — replace then close overlay; fallback on throw; verify implement OK
- 2026-09-05T19:20 T-01 done — same-origin `window.open('')` + `Creating...` document; verify implement OK
- 2026-09-05T19:16 plan.md and tasks.md written (cycle 4)
- 2026-09-05T16:41 plan.md and tasks.md written (cycle 2)
- 2026-09-05T16:45 T-01 done — card rewrite `/api/projects/:driveFolderId/` keeps trailing slash; verify implement OK
- 2026-09-05T16:48 T-02 done — full audit: 0 findings in `next.config.ts`; baseline WARN `.DS_Store` unchanged
- 2026-09-05T16:48 cycle 2 implement complete: 2/2 done, 0 blocked
- 2026-09-05T18:25 plan.md and tasks.md written (cycle 3)
- 2026-09-05T18:32 T-01 done — `projectCardHref`; verify implement OK
- 2026-09-05T18:32 T-02 done — list `Link` new tab
- 2026-09-05T18:33 T-03 done — create opens card in new tab
- 2026-09-05T18:33 T-04 done — heading `Project` accent / name foreground
- 2026-09-05T18:33 T-05 done — Update rates and Close period `PrimaryButton`
- 2026-09-05T18:35 T-06 done — audit touched files: 0 ERR, 0 WARN; baseline WARN `.DS_Store` unchanged
- 2026-09-05T18:35 cycle 3 implement complete: 6/6 done, 0 blocked
