# WF-13: Tasks

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Copy `feptm-analysis/docs/ui-style/foreach-partners-logo.png` byte-identical to `feptm-web/public/foreach-partners-logo.png`; MUST NOT download foreachpartners.com, crop `header.png`, or re-export the PNG | FR-PROJECT-001 | — | done | 2026-09-04T13:05 |
| T-02 | Header: in `feptm-web/src/components/AppHeader.tsx` replace `span.app-header__mark` with `<img src="/foreach-partners-logo.png" alt="" width={32} height={32} />` plus wordmark `ForEach Partners`; in `feptm-web/src/app/globals.css` delete `.app-header__mark` (`mask` / `currentColor`) and add `.app-header__logo` 32×32 `object-fit: contain`; leave `:root` tokens, buttons, cards, heading, overlay unchanged | FR-PROJECT-001 | T-01 | done | 2026-09-04T13:06 |
| T-03 | Delete invented `feptm-web/public/shaking-hands.svg`; do not leave a CSS `url('/shaking-hands.svg')` reference | FR-PROJECT-001 | T-02 | done | 2026-09-04T13:07 |
| T-04 | Audit: full repo audit — zero ERR, zero WARN in touched files (`feptm-web/public/foreach-partners-logo.png`, `feptm-web/src/components/AppHeader.tsx`, `feptm-web/src/app/globals.css`; confirm `shaking-hands.svg` gone). No feptm-server files | FR-PROJECT-001 | T-03 | done | 2026-09-04T13:08 |
