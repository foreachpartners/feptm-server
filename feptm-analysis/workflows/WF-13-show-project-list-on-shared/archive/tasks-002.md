# WF-13: Tasks

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Tokens + chrome CSS: replace invented teal in `feptm-web/src/app/globals.css` with snapshot/live dark tokens (`--background`, `--foreground`, `--muted`, `--accent`, `--on-accent`, `--surface`, `--border`, `--radius`, `--font-sans`, `--font-mono`); restyle header, primary/secondary buttons (no 999px pill, no `#041214`), card grid, heading scale, overlay fields; `color-scheme: dark` only | FR-PROJECT-001 | — | done | 2026-09-04T12:20 |
| T-02 | Fonts: load Geist + Geist Mono in `feptm-web/src/app/layout.tsx` via `next/font`; map onto `--font-sans` / `--font-mono`; do not use Arial as the designed face | FR-PROJECT-001 | T-01 | done | 2026-09-04T12:25 |
| T-03 | Logo + header: copy `feptm-analysis/docs/ui-style/foreach-partners-logo.png` to `feptm-web/public/foreach-partners-logo.png`; wire `/foreach-partners-logo.png` as `<img>` 32px in `AppHeader.tsx` + wordmark `ForEach Partners`; no nav, no Start Project, no theme toggle; MUST NOT fetch live SVG, crop `header.png`, or use CSS mask; delete `public/shaking-hands.svg` | FR-PROJECT-001 | T-02 | done | 2026-09-04T12:30 |
| T-04 | Dashboard surfaces: keep FR copy in `feptm-web/src/features/projects/ProjectDashboard.tsx`; card grid markup in `feptm-web/src/features/projects/ProjectNameList.tsx`; Cancel remains `.secondary-button` in `CreateProjectOverlay.tsx`; `PrimaryButton.tsx` stays token-only (no local palette). Optional muted footer chrome from `footer.png` tokens, no landing columns | FR-PROJECT-001 | T-03 | done | 2026-09-04T12:35 |
| T-05 | Audit: full repo audit — zero ERR, zero WARN in touched files | FR-PROJECT-001 | T-04 | done | 2026-09-04T12:40 |
