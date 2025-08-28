# Secuflow Rebuild

Monorepo with Django API backend and Next.js frontend.

## Structure

- `backend/` — Django REST API (`accounts` app, JWT auth)
- `frontend/` — Next.js (App Router, Tailwind v4, shadcn/ui, Axios)

## Prerequisites

- Python 3.11+
- Node.js 18+ and pnpm

## Quick Start

### Backend

```powershell
cd backend
# first time
python -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
# run
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

- API base: `http://localhost:8000/api/`
- Health check: `GET /api/health/`
- Create admin:
```powershell
.\venv\Scripts\python.exe manage.py createsuperuser
```

### Frontend

```powershell
cd frontend
pnpm install
pnpm dev
```
- App: `http://localhost:3000`
- Config: `frontend/.env.local`
  - `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api`

## Notes
- CORS is enabled in backend settings.
- JWT tokens are read from `localStorage` (`access_token`) by the Axios client.
- Tailwind colors follow shadcn/ui tokens in `app/globals.css`.
