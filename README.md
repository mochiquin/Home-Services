# Secuflow Code Analysis Platform

> A modern code analysis platform built with Django + Next.js + TNM

## 🚀 Quick Start

### Prerequisites
- Docker Desktop
- Java JDK 11+
- Node.js 18+

### Setup & Run

```bash
# 1. Clone and setup
git clone <repository-url>
cd Secuflow_Rebuild
cp docker.env .env

# 2. Start backend services
docker-compose up -d --build

# 3. Start frontend
cd frontend
pnpm install
pnpm dev
```

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
```bash
# Access MySQL
docker-compose exec mysql mysql -u root -p

# Run migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser
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