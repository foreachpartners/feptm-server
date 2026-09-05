# WF-14: Technical Plan

Implements: FR-PROJECT-001, FR-CREATE-001, FR-SHEET-001, FR-SYNC-001, FR-SYNC-RATES-001, FR-PAYMENT-001
AR references: AR-WEBARCH-001, AR-REACT-001, AR-NEXTJS-001, AR-HTML-001, AR-TYPESCRIPT-001, AR-LINEAGE-001, AR-LINEAGE-002, AR-WRITING-001, AR-WORKSPACE-001, AR-SECRETS-001
Context: [context.md](context.md)

**Workflow:** WF-14-project-card-it-opens-same (large ceremony)
**Repos:** web (`feptm-web`); feptm-server unchanged
**Task:** Cycle 5 — after create, the new tab MUST leave `about:blank` in Chrome and Yandex during `POST /api/projects/create` and after the overlay closes. Cycle 4 `window.open('')` plus `document.write` still commits `about:blank` in the address bar. Stop empty-URL `window.open`. Add a same-origin static placeholder at `feptm-web/public/creating.html`. Open that HTTP URL on the Create gesture, then `location.replace` the card href. Close the overlay only after a successful replace. On replace failure close the placeholder and fall back to `window.open`. On create error close the placeholder.
**baseline_policy:** `fix_err` — baseline has 0 ERR, 1 WARN (`.gitignore` missing `.DS_Store`). Do not remediate the existing WARN. Enforce zero new violations in touched files.

## Architecture Overview

Cycles 1–3 already ship the card at `/projects/{drive_folder_id}`, the slash-preserving rewrite, list `Link` `target="_blank"`, heading colors, and command-row `PrimaryButton`. Cycle 4 changed the create-tab handoff to `window.open('', '_blank')` plus `document.write`. This cycle changes only that placeholder open. Keep the Cycle 4 `useCreateProject` replace / fallback / error-close handoff.

Today in Chrome and Yandex after Cycle 4:

- `feptm-web/src/features/projects/CreateProjectOverlay.tsx` `handleSubmit` calls `window.open('', '_blank')`, then `document.open` / `document.write` / `document.close` with title `Creating...`
- `feptm-web/src/features/projects/useCreateProject.ts` `onSuccess` calls `cardTab.location.replace(cardHref)`, then `cardTab.opener = null`, then `closeCreateOverlay()`
- The new tab stays on `about:blank` in the address bar during `POST /api/projects/create` and after the overlay closes

Chromium treats `window.open('')` and `window.open()` as `window.open('about:blank')` for the address bar. An empty or `about:blank` open commits a `about:blank` NavigationEntry. `document.write` MAY inherit origin and `location.href` in the DOM. The browser process does not learn about that URL update. The address bar stays `about:blank`. `location.replace` after the async POST onto that committed `about:blank` tab often fails without throwing.

A real same-origin HTTP URL in `window.open` does not commit the initial empty document. The address bar shows `/creating.html` during the POST. `location.replace` from that loaded same-origin document to the card path works.

```mermaid
flowchart LR
  Submit["Create handleSubmit"] --> Open["window.open creating.html"]
  Open --> Post["POST /api/projects/create"]
  Post -->|success| Replace["cardTab.location.replace href"]
  Replace --> Close["closeCreateOverlay"]
  Replace -->|throws| Fallback["close tab then window.open href"]
  Post -->|error| CloseTab["cardTab.close"]
```

MUST NOT:

- Change `feptm-web/src/features/projects/ProjectNameList.tsx` (list `Link` stays `target="_blank"`)
- Change card heading colors or command-row buttons in `feptm-web/src/features/projects/ProjectCard.tsx`
- Change `feptm-web/src/features/projects/useCreateProject.ts` (replace / fallback / error-close stay)
- Change feptm-server, OpenAPI, proto, or `feptm-web/next.config.ts`
- Call `window.open('')` or `window.open('about:blank')` anywhere
- Call `document.write` / `document.open` / `document.close` on the placeholder tab
- Open a sized window (`width` / `height` or other window features on the placeholder)
- Navigate the dashboard tab to the card (`router.push`)
- Open `/projects/new` (`feptm-web/src/app/projects/new/page.tsx` redirects to `/`)
- Add an App Router page for the placeholder
- Implement FR-THEME-001
- Change create copy, validation, busy lock, or error text

## Proto Contracts

No proto. N/A.

## REST API

No new endpoints. No server change.

Unchanged client paths in `feptm-web/src/lib/api/projects.ts`:

- `POST /api/projects/create` — 200 `ProjectMetaResponse`; `drive_folder_id` is required to build the card URL
- `GET /api/projects/{drive_folder_id}/` — card (unchanged)
- `GET /api/projects/` — list invalidate after success (unchanged)

Spec source: FastAPI `/openapi.json`. No OpenAPI YAML file in the repo.

### OpenAPI Schema Changes

No schema changes.

## Database Schema

No migrations.

## Implementation Details

### 1. Static placeholder — FR-CREATE-001 — `feptm-web/public/creating.html`

Add a static file. Next.js serves `public/` at the site root. No rewrite. No `next.config.ts` change.

MUST:

- File path: `feptm-web/public/creating.html`
- Served URL: `/creating.html`
- `<title>` text: `Creating...` (same text as the overlay status in `CreateProjectOverlay.tsx`)
- Static markup only. Visible body MAY repeat `Creating...` so the tab is not an empty white page
- `lang="en"` to match `feptm-web/src/app/layout.tsx`

MUST NOT:

- Interpolate the project name or any user input (XSS)
- Add scripts, analytics, or inline event handlers
- Add `src/app/creating/page.tsx` or any App Router route
- Change `feptm-web/src/app/layout.tsx`
- Treat this stub as an AR-HTML-001 App Router page (`header` / `main` / `footer` in the root layout do not apply to `public/`)

### 2. Placeholder tab — FR-CREATE-001 — `feptm-web/src/features/projects/CreateProjectOverlay.tsx`

In `handleSubmit`, after the empty-name and pending guards, open the tab on the user gesture, then pass that `Window` into `useCreateProject`.

MUST:

- Resolve the placeholder with `new URL('/creating.html', window.location.origin).href` (AR-NEXTJS-001: no hardcoded host)
- Call `window.open(placeholderHref, '_blank')` with no features string
- Pass `{ cardTab, name: trimmedName }` into `createProject.mutate`
- If `window.open` returns `null` (blocked), still run create

MUST NOT:

- Pass `''` or `'about:blank'` as the URL
- Pass a features string (`noopener` returns `null` and blocks later replace; `width`/`height` opens a window)
- Call `document.write`, `document.open`, or `document.close` on the opened `Window`
- Change overlay markup, validation, busy lock, Cancel, backdrop, or error text

Keep `CreateProjectVariables.cardTab: Window | null` in `feptm-web/src/features/projects/useCreateProject.ts`.

### 3. Success and error handoff — FR-CREATE-001 — unchanged `feptm-web/src/features/projects/useCreateProject.ts`

Do not edit this file. Cycle 4 already implements the handoff.

Keep:

1. Missing `drive_folder_id`: `cardTab?.close()`, overlay stays.
2. `cardTab` non-null: `location.replace` the absolute `projectCardHref` from `feptm-web/src/features/projects/projectCardHref.ts` resolved with `new URL(href, window.location.origin).href`. Then `cardTab.opener = null`, then `closeCreateOverlay()`, then `invalidateQueries(['projects'])`.
3. `location.replace` throws: `cardTab.close()`, then `window.open(href, '_blank', 'noopener,noreferrer')` with no size features, then close overlay and invalidate.
4. `cardTab` is `null`: same fallback `window.open`, then close overlay and invalidate.
5. `onError`: `variables.cardTab?.close()`. Overlay stays open with `Failed to create the project. Try again later.`

MUST NOT:

- Close the overlay before `location.replace` succeeds or the fallback `window.open` runs
- Leave a placeholder tab open after create error or after a failed replace
- `router.push` the dashboard tab
- Change `mutationFn` or `createProject` in `feptm-web/src/lib/api/projects.ts`

### Out of scope

- `ProjectNameList.tsx` list `Link`
- `ProjectCard.tsx` heading and command-row buttons
- `ClosePeriodModal.tsx`
- `useCreateProject.ts` handoff
- `projectCardHref.ts` path shape
- `src/app/projects/new/page.tsx`
- feptm-server, OpenAPI YAML, proto, `next.config.ts`, API client contracts
- FR-THEME-001
- Remediation of the baseline WARN `.DS_Store`
- A new test runner
- Auth
- User-facing copy

## Security Considerations

- Placeholder `window.open` MUST omit a features string so the opener keeps a live `Window` reference.
- Fallback `window.open` MUST use `noopener,noreferrer` and MUST omit size features.
- After a successful `location.replace`, set `cardTab.opener = null`.
- `creating.html` MUST be a static file. DO NOT interpolate the project name (XSS).
- Placeholder and card hrefs stay same-origin paths resolved against `window.location.origin`. DO NOT hardcode a host.
- Browser calls stay same-origin `/api/*`. No secrets. DO NOT log request or response bodies.

## Config Changes

No new env keys. Prefix N/A for web. Keep `NEXT_PUBLIC_API_URL` as the rewrite origin.
