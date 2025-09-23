# Secuflow Backend (Django REST API)

## 🏗️ Architecture

The backend is built with Django REST Framework and provides comprehensive APIs for:

- **User Management** (`accounts/`) - Authentication, user profiles
- **Project Management** (`projects/`) - Project lifecycle, membership
- **Contributors Analysis** (`contributors/`) - Developer contribution metrics
- **Coordination Analysis** (`coordination/`) - Team coordination analysis
- **Risk Assessment** (`risks/`) - Security and code quality analysis
- **TNM Integration** (`tnm_integration/`) - Code analysis tool integration

## 🚀 Quick Setup

### Local Development

```powershell
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver 0.0.0.0:8000
```

### Docker Development (Recommended)

```bash
# From project root
docker-compose up -d --build

# Access container for Django commands
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
```

## 🔗 API Endpoints

| Service | URL | Description |
|---------|-----|-------------|
| **Health Check** | `GET /api/health/` | Service status |
| **Authentication** | `/api/auth/` | Login, register, profile |
| **Users** | `/api/users/` | User management |
| **Projects** | `/api/projects/` | Project operations |
| **Contributors** | `/api/contributors/` | Contribution analysis |
| **Coordination** | `/api/coordination/` | Team coordination |
| **Risks** | `/api/risks/` | Risk assessment |
| **TNM** | `/api/tnm/` | Code analysis |

## 🔐 Authentication

- **JWT Authentication** via `djangorestframework-simplejwt`
- **Token Endpoints**:
  - `POST /api/auth/login/` - Obtain tokens
  - `POST /api/auth/token/refresh/` - Refresh access token
  - `POST /api/auth/logout/` - Logout (blacklist token)

## 🛠️ Common Commands

```powershell
# Database operations
python manage.py showmigrations
python manage.py makemigrations
python manage.py migrate

# User management
python manage.py createsuperuser
python manage.py shell

# Development tools
python manage.py check
python manage.py collectstatic
```

## 📁 Project Structure

```
backend/
├── accounts/           # User authentication & management
├── projects/           # Project lifecycle management  
├── contributors/       # Developer contribution analysis
├── coordination/       # Team coordination metrics
├── risks/             # Security & quality assessment
├── tnm_integration/   # TNM tool integration
├── common/            # Shared utilities & middleware
├── api/               # Main API routing
├── secuflow/          # Django project settings
├── tnm_output/        # TNM analysis results
├── tnm_repositories/  # Git repository workspace
└── manage.py          # Django management script
```

## 🔧 Middleware Features

The backend includes custom middleware for:

- **API Logging** - Request/response tracking
- **Global Exception Handling** - Unified error responses
- **Response Envelope** - Consistent API response format
- **Content Rendering** - Automatic DRF response processing

## 🗄️ Database

- **Development**: SQLite (default)
- **Production**: MySQL 8.0 (via Docker)
- **Migrations**: All models include proper migrations
- **Admin Interface**: Available at `/admin/`

## 📊 Logging

Simplified logging configuration:
- **Console output** for all logs
- **Debug level** in development
- **Module-based** logger names (`__name__`)

## 🧪 Testing

```bash
# Run tests
python manage.py test

# Check code style
flake8 .

# Type checking
mypy .
```
