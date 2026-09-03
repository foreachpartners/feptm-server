# FEPTM Web

Next.js frontend for the FEPTM shared project dashboard. The browser calls
same-origin `/api/*` routes; Next.js proxies them to `feptm-server`.

## Prerequisites

- Node.js 20 (see `.nvmrc`)
- pnpm 9 or later
- A local `feptm-server` instance on port 8000, or another configured upstream

## First-time setup

1. Copy `env.example` to `.env.local`.
2. Set `NEXT_PUBLIC_API_URL` to the `feptm-server` HTTP origin.
3. Run `pnpm install`.
4. Run `pnpm dev`.

## Verification

Run `pnpm typecheck`, `pnpm lint`, and `pnpm format:check` before beginning a
workflow. `pnpm build` verifies the production build once the backend URL is
configured.

## Source layout

- `src/app` — routes and route composition
- `src/components` — reusable presentation components
- `src/features` — feature-specific UI and state
- `src/lib/api` — typed HTTP client
- `src/lib/utils` — shared utilities
- `src/types` — frontend domain types
