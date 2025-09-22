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
├── docker-compose.yml      # Docker services
├── backend/                # Django API
│   ├── tnm_output/         # Analysis results
│   └── tnm_repositories/   # Git repos
├── frontend/               # Next.js app
└── tnm/                    # Analysis tool
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