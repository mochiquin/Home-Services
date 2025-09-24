# Secuflow Code Analysis Platform

> A modern code analysis platform built with Django + Next.js + TNM

## 🚀 Quick Start

### Prerequisites
- Docker Desktop
- Java JDK 11+
- Node.js 18+

### Setup & Run

```bash
# 1. Clone and setup (including submodules)
git clone --recursive <repository-url>
cd Secuflow_Rebuild
cp docker.env .env

# If you already cloned without --recursive, initialize submodules:
git submodule update --init --recursive

# 2. Build TNM CLI locally (first time or after TNM changes)
# Requires JDK 11+
./tnm/gradlew :cli:shadowJar

# 3. Start backend services
docker-compose up -d --build

# 4. Initialize database (first time only)
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser --username admin --email admin@example.com --noinput
docker-compose exec backend python manage.py shell -c "from django.contrib.auth.models import User; u = User.objects.get(username='admin'); u.set_password('admin123'); u.save(); print('Password set successfully')"

# 5. Start frontend
cd frontend
pnpm install
pnpm dev
```

### Default Admin Account
- **Username**: admin
- **Email**: admin@example.com  
- **Password**: admin123

### Access URLs
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Database**: localhost:3307
- **Cache**: localhost:6379

## 📁 Project Structure

```
Secuflow_Rebuild/
├── 📄 docker-compose.yml        # Docker orchestration
├── 📄 docker.env                # Environment variables
├── 📄 .env                      # Runtime configuration
├── 📂 backend/                  # Django REST API
│   ├── 🐳 Dockerfile
│   ├── ⚙️ manage.py
│   ├── 📦 requirements.txt
│   ├── 📂 accounts/             # User management APIs
│   ├── 📂 projects/             # Project management APIs
│   ├── 📂 contributors/         # Contributor analysis APIs
│   ├── 📂 coordination/         # Coordination analysis APIs
│   ├── 📂 risks/               # Risk assessment APIs
│   ├── 📂 tnm_integration/     # TNM tool integration
│   ├── 📂 common/              # Shared utilities & middleware
│   ├── 📂 api/                 # Main API routing
│   ├── 📂 secuflow/            # Django settings
│   ├── 📂 tnm_output/          # TNM analysis results
│   ├── 📂 tnm_repositories/    # Git repository workspace
│   └── ⚙️ tnm_config.json      # TNM configuration
├── 📂 frontend/                 # Next.js application
│   ├── 🐳 Dockerfile
│   ├── 📦 package.json
│   ├── ⚙️ next.config.ts
│   └── 📂 app/                 # App pages & components
├── 📂 tnm/                     # TNM analysis tool (submodule)
│   ├── 🐳 Dockerfile
│   ├── ⚙️ build.gradle.kts
│   ├── 🔧 gradlew
│   └── 📂 cli/                 # Command line interface
├── 📄 Postman_Environment.json # API testing environment
└── 📄 Secuflow_API_Collection.json # API test collection
```

## 🛠️ Services

| Service | Port | Description |
|---------|------|-------------|
| **mysql** | 3307 | Database |
| **redis** | 6379 | Cache |
| **backend** | 8000 | Django API |
| **frontend** | 3000 | Next.js (local) |
| **tnm** | - | Analysis tool |

## 🔍 TNM Usage

### Basic Commands
```bash
# View help
docker-compose exec tnm java -jar /app/tnm-cli.jar --help

# Analyze repository
git clone https://github.com/user/repo.git backend/tnm_repositories/repo

# Run analysis
docker-compose exec tnm java -jar /app/tnm-cli.jar FilesOwnershipMiner \
  --repository /data/repositories/repo/.git main
```

### Output Files
- `DeveloperKnowledge.json` - Developer knowledge
- `FilesOwnership.json` - File ownership
- `PotentialAuthorship.json` - Potential authorship
- `AssignmentMatrix` - Assignment data

**Output location**: `backend/tnm_output/`

## 🔑 ID format in APIs
- Resource IDs (e.g., users, projects) are UUID strings.
- Path placeholders `{id}` in endpoints expect UUIDs, e.g. `/api/projects/projects/{id}/`.

## 🚨 Troubleshooting

### Common Issues

**Java not found**
```bash
# Install JDK 11+ from https://adoptium.net/
java --version
```

**Docker not running**
```bash
# Start Docker Desktop
docker info
```

**Port conflicts**
```bash
# Check ports
netstat -ano | findstr :3000
netstat -ano | findstr :8000
```

**Service logs**
```bash
docker-compose logs backend
docker-compose logs tnm
```

### Cleanup
```bash
# Stop services
docker-compose down

# Clean environment
docker-compose down -v
docker system prune -f
```

## 👨‍💻 Development

### Service Management
```bash
# Start/stop
docker-compose up -d
docker-compose down

# Rebuild
docker-compose up -d --build

# View logs
docker-compose logs -f [service]
```

### Database Operations

#### Initial Setup (First Time)
```bash
# 1. Apply database migrations to create tables
docker-compose exec backend python manage.py migrate

# 2. Create superuser account
docker-compose exec backend python manage.py createsuperuser --username admin --email admin@example.com --noinput

# 3. Set superuser password
docker-compose exec backend python manage.py shell -c "from django.contrib.auth.models import User; u = User.objects.get(username='admin'); u.set_password('admin123'); u.save(); print('Password set successfully')"
```

#### Daily Operations
```bash
# Access MySQL database
docker-compose exec mysql mysql -u root -p

# Access database with secuflow user
docker-compose exec mysql mysql -u secuflow -psecuflow123 secuflow

# Show all tables
docker-compose exec mysql mysql -u secuflow -psecuflow123 secuflow -e "SHOW TABLES;"

# Check migration status
docker-compose exec backend python manage.py showmigrations

# Create new migrations (after model changes)
docker-compose exec backend python manage.py makemigrations

# Apply new migrations
docker-compose exec backend python manage.py migrate
```

#### Database Reset (Development Only)
```bash
# Reset database (WARNING: This will delete all data)
docker-compose down
docker volume rm secuflow_rebuild_mysql_data
docker-compose up -d
docker-compose exec backend python manage.py migrate
```

### Development Workflow
1. Start backend: `docker-compose up -d`
2. Start frontend: `cd frontend && pnpm dev`
3. Develop and test
4. Stop: `docker-compose down`

## 📚 Resources

- [Django Docs](https://docs.djangoproject.com/)
- [Next.js Docs](https://nextjs.org/docs)
- [Docker Docs](https://docs.docker.com/)

## 🤝 Contributing

1. Fork the project
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open Pull Request

---

**Happy Coding! 🎉**

## 🔧 Backend (Django REST API)

### Architecture

The backend is built with Django REST Framework and provides comprehensive APIs for:

- **User Management** (`accounts/`) - Authentication, user profiles, Git credentials
- **Project Management** (`projects/`) - Project lifecycle, membership, Git integration
- **Contributors Analysis** (`contributors/`) - Developer contribution metrics
- **Coordination Analysis** (`coordination/`) - Team coordination analysis
- **Risk Assessment** (`risks/`) - Security and code quality analysis
- **TNM Integration** (`tnm_integration/`) - Code analysis tool integration

### API Endpoints

| Service | URL | Description |
|---------|-----|-------------|
| **Health Check** | `GET /api/health/` | Service status |
| **Authentication** | `/api/auth/` | Login, register, profile |
| **Users** | `/api/users/` | User management |
| **Git Credentials** | `/api/git-credentials/` | Git authentication management |
| **Projects** | `/api/projects/` | Project operations |
| **Contributors** | `/api/contributors/` | Contribution analysis |
| **Coordination** | `/api/coordination/` | Team coordination |
| **Risks** | `/api/risks/` | Risk assessment |
| **TNM** | `/api/tnm/` | Code analysis |

### Authentication

- **JWT Authentication** via `djangorestframework-simplejwt`
- **Token Endpoints**:
  - `POST /api/auth/login/` - Obtain tokens
  - `POST /api/auth/token/refresh/` - Refresh access token
  - `POST /api/auth/logout/` - Logout (blacklist token)

### Git Integration Features

- **Multi-provider Support**: GitHub, GitLab, Bitbucket
- **Authentication Methods**: 
  - HTTPS Personal Access Tokens
  - SSH Private Keys
  - Username/Password (Basic Auth)
- **Encrypted Credential Storage**: Secure credential management
- **Permission Error Handling**: Detailed error analysis and solutions
- **Repository Validation**: Pre-clone access verification
- **Retry Mechanisms**: Recovery after authentication fixes

### Database

- **Development**: SQLite (default)
- **Production**: MySQL 8.0 (via Docker)
- **Migrations**: All models include proper migrations
- **Admin Interface**: Available at `/admin/`

### Common Backend Commands

```bash
# Database operations
docker-compose exec backend python manage.py showmigrations
docker-compose exec backend python manage.py makemigrations
docker-compose exec backend python manage.py migrate

# User management
docker-compose exec backend python manage.py createsuperuser
docker-compose exec backend python manage.py shell

# Development tools
docker-compose exec backend python manage.py check
docker-compose exec backend python manage.py collectstatic
```

### API Documentation

The project includes comprehensive API documentation through Postman:

- **Environment File**: `Postman_Environment.json` - Contains all necessary variables
- **Collection File**: `Secuflow_API_Collection.json` - Complete API test suite

### Middleware Features

- **Request/Response Logging**: Comprehensive API request tracking
- **Global Exception Handling**: Unified error response format
- **API Response Envelope**: Consistent response structure across all endpoints
- **Content Rendering**: Automatic DRF response processing
- **Git Error Analysis**: Intelligent error detection and solution guidance

## 📦 Version Control & Cleanup

### Cleaned Files
- ✅ Removed empty `backend/backend/` directory
- ✅ Deleted empty log files and `logs/` directory (using console logging)
- ✅ Removed empty `backend/tnm-cli.jar` file
- ✅ Cleaned all `__pycache__/` directories
- ✅ Migrated `backend/README.md` to root README and deleted duplicate

### Gitignore Coverage
- Virtual environments (`venv/`, `.venv/`)
- Python cache files (`__pycache__/`, `*.pyc`)
- Log files (`*.log`, `logs/`)
- Environment files (`.env*`)
- TNM output directories (`tnm_output/`, `tnm_repositories/`)
- Binary artifacts (`tnm-cli.jar`)
- Development tools cache