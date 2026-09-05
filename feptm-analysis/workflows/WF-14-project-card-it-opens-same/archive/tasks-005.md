# WF-14: Tasks

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Placeholder: add static `feptm-web/public/creating.html` — `lang="en"`, `<title>` `Creating...`, static markup only, body MAY repeat `Creating...`. Do not interpolate user input. Do not add scripts or an App Router page. Do not change `feptm-web/src/app/layout.tsx` or `feptm-web/next.config.ts`. | FR-CREATE-001 | — | done | 2026-09-05T19:53 |
| T-02 | Overlay: in `feptm-web/src/features/projects/CreateProjectOverlay.tsx` `handleSubmit` stop `window.open('')` and `document.write`. Resolve `new URL('/creating.html', window.location.origin).href`, call `window.open(placeholderHref, '_blank')` with no features, pass `{ cardTab, name }` into `useCreateProject`. If open is null, still mutate. Do not change overlay markup, validation, or error text. Do not edit `feptm-web/src/features/projects/useCreateProject.ts`. | FR-CREATE-001 | T-01 | done | 2026-09-05T19:54 |
| T-03 | Audit: full repo audit — zero ERR, zero WARN in touched files | FR-PROJECT-001, FR-CREATE-001, FR-SHEET-001, FR-SYNC-001, FR-SYNC-RATES-001, FR-PAYMENT-001 | T-02 | done | 2026-09-05T19:55 |
