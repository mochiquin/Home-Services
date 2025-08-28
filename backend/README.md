# Backend (Django API)

## Setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
```

## Run

```powershell
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

- Base URL: `http://localhost:8000`
- API Base: `http://localhost:8000/api/`
- Health: `GET /api/health/`

## Auth
- JWT via `djangorestframework-simplejwt`
- Obtain/refresh endpoints exposed in `accounts/urls.py`

## Common
```powershell
.\venv\Scripts\python.exe manage.py createsuperuser
.\venv\Scripts\python.exe manage.py showmigrations
.\venv\Scripts\python.exe manage.py makemigrations
.\venv\Scripts\python.exe manage.py migrate
```
