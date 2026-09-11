# Formal Platform — Web studio

Minimal Next.js App Router SaaS studio for the Formal Platform (Phase 4).

## Prerequisites

- Node.js 18+
- Formal Platform API running (default `http://localhost:8000`) with CORS allowing `http://localhost:3000`

## Setup

From the **monorepo root** (npm workspaces):

```bash
npm install
cp apps/web/.env.example apps/web/.env.local
npm run dev:web
```

Or from this package:

```bash
cd apps/web
npm install
cp .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Next.js dev server (port 3000) |
| `npm run build` | Production build |
| `npm run start` | Serve production build |
| `npm run lint` | ESLint via `next lint` |

Root convenience scripts: `dev:web`, `build:web`, `lint` (see repository `package.json`).

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Formal Platform API base URL |

## Pages

- `/` — Landing / studio home
- `/studio` — Meta, create organization, create/list projects
- `/studio/certificates` — Issue demo certificate (`allow_unverified: true`, `require_lean: false` for local demos)

## API expectations

- `GET /api/v1/meta`
- `POST /api/v1/organizations` — `{ name, slug }`
- `POST /api/v1/projects` — `{ organization_id, workspace_id, name, description? }`
- `GET /api/v1/projects?organization_id=&workspace_id=`
- `POST /api/v1/certificates/demo/issue` — demo issuer (Lean optional when `require_lean: false`)

If the API is down, studio pages show a graceful error instead of crashing.
