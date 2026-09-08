# WF-14: Tasks

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Create overlay: replace secondary button child text `Cancel` with `Close` in `feptm-web/src/features/projects/CreateProjectOverlay.tsx`. Keep `className="secondary-button"`, `disabled={isBusy}`, and `handleCancel`. | FR-CREATE-001 | — | done | 2026-09-08T10:30 |
| T-02 | Close period modal: replace secondary button child text `Cancel` with `Close` in `feptm-web/src/features/projects/ClosePeriodModal.tsx`. Keep `className="secondary-button"`, `disabled={isCancelDisabled}`, and `handleCancel`. Do not change `Close period` in `feptm-web/src/features/projects/ProjectCard.tsx`. | FR-PAYMENT-001 | T-01 | done | 2026-09-08T10:30 |
| T-03 | Audit: full repo audit — zero ERR, zero WARN in touched files (`CreateProjectOverlay.tsx`, `ClosePeriodModal.tsx`) | FR-CREATE-001, FR-PAYMENT-001 | T-02 | done | 2026-09-08T10:32 |
