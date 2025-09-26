# Frontend (Next.js)

Tech: Next.js App Router, Tailwind v4, shadcn/ui, Axios, React Hook Form, Zod.

## Setup

```powershell
cd frontend
pnpm install
```

## Environment
Create `.env.local`:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
NEXT_PUBLIC_API_TIMEOUT=10000
```

## Run

```powershell
pnpm dev
```
- Local: `http://localhost:3000`

## Project Notes
- Global styles and tokens in `app/globals.css` (shadcn/ui colors).
- Axios client at `lib/api.ts` reads `localStorage.access_token` and `NEXT_PUBLIC_API_*`.
- UI components from `shadcn/ui` in `components/ui/`.
