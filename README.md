# Home Services Platform

> A comprehensive home services booking platform connecting homeowners with professional service providers

## 📋 Project Overview

The Home Services Platform is a full-stack web application that connects homeowners with professional service providers. Built with Django REST Framework backend and React/Next.js frontend, the platform enables users to discover, book, and manage various home services including inspections, repairs, maintenance, and specialized services.

### 🎯 Core Features

#### 🔐 User Registration & Authentication
- **User Registration**: Complete profile creation with personal information
  - Name, age, mobile, email
  - Country of citizenship, preferred language
  - COVID-19 vaccination status
  - Credit card information, trade/profession
- **Secure Login**: Username/password authentication with security measures
- **Social Login**: Integration with Google/Facebook/WeChat (optional)
- **Privacy Protection**: Secure handling of personal information

#### 🏠 Special General Service
- **Home Inspection**: Comprehensive house inspection service
- **Safety Assessment**: Identification of urgent repair needs
- **Service Recommendations**: Customized list of required work
- **Flexible Booking**: Multi-hour to multi-day service options
- **Multi-service Support**: Workers can handle multiple jobs simultaneously

#### 📦 Service Packages
- **Bundle Services**: Complete service packages at discounted rates
- **Customization Options**: Tailored packages for cost optimization
- **Rich Media**: Photos, descriptions, user reviews
- **Advanced Features**: Search, sort, compare functionality
- **Pricing Transparency**: Clear pricing structure

#### 🔍 Specific Service Booking
- **Location-based Services**: Find nearby service providers
- **Map Integration**: Google Maps API integration
- **Provider Profiles**: Detailed service provider information
- **COVID Restrictions**: Real-time restriction and availability updates
- **Smart Matching**: Intelligent provider-client matching

#### 💳 Additional Features
- **Payment Processing**: Secure payment methods
- **Booking Management**: Confirmation letters, QR codes
- **Communication**: Payment requests, reminder system
- **Promotions**: Voucher and discount code system

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed and running
- Git for version control

### Setup & Installation

```bash
# 1. Clone the repository
git clone https://github.com/mochiquin/Home-Services
cd Home-Services

# 2. Start all services with Docker
docker-compose up -d --build

# 3. Create admin user (first time setup)
docker-compose exec backend python create_admin.py


```

### Default Admin Account
- **Username**: admin
- **Email**: admin@homeservices.com
- **Password**: admin123456

### Service Endpoints
- **Backend API**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin/
- **MySQL Database**: localhost:3307
- **Redis Cache**: localhost:6379

### API Testing
Use the following endpoints to test the API:
- **Get JWT Token**: `POST http://localhost:8000/api/token/`
- **Services**: `GET http://localhost:8000/api/services/`
- **Providers**: `GET http://localhost:8000/api/providers/`
- **Bookings**: `GET http://localhost:8000/api/bookings/`

## 📁 Project Structure

```
Home-Services/
├── 📄 docker-compose.yml        # Docker orchestration
├── 📄 docker.env                # Environment variables
├── 📄 .env                      # Runtime configuration
├── 📂 backend/                  # Django REST API
│   ├── 🐳 Dockerfile
│   ├── ⚙️ manage.py
│   ├── 📦 requirements.txt
│   ├── 📂 accounts/             # User authentication & profiles
│   ├── 📂 services/             # Service management
│   ├── 📂 bookings/             # Booking system
│   ├── 📂 providers/            # Service provider management
│   ├── 📂 payments/             # Payment processing
│   ├── 📂 notifications/        # Notification system
│   ├── 📂 reviews/              # Review and rating system
│   └── 📂 api/                  # Main API routing
├── 📂 frontend/                 # React/Next.js application
│   ├── 🐳 Dockerfile
│   ├── 📦 package.json
│   ├── ⚙️ next.config.js
│   ├── 📂 components/           # Reusable UI components
│   ├── 📂 pages/                # Application pages
│   ├── 📂 hooks/                # Custom React hooks
│   ├── 📂 services/             # API service layer
│   └── 📂 utils/                # Utility functions
└── 📂 docker/                   # Docker configuration files
```

## 🛠️ Services Architecture

| Service | Port | Description |
|---------|------|-------------|
| **mysql** | 3307 | Primary database |
| **redis** | 6379 | Cache & sessions |
| **backend** | 8000 | Django REST API |
| **frontend** | 3000 | React application |

## 🔧 Backend (Django REST Framework)

### Core Applications

The backend consists of 7 main Django applications:

- **`accounts`** - Custom user model, authentication, and user profile management
- **`services`** - Service catalog, categories, requirements, and service areas
- **`providers`** - Service provider profiles, documents, and availability
- **`bookings`** - Complete booking lifecycle with status tracking
- **`payments`** - Payment processing and transaction management
- **`reviews`** - User feedback and rating system
- **`notifications`** - Communication and notification management

### API Endpoints

#### 🔐 Authentication
| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|---------------|
| `/api/token/` | POST | Get JWT access/refresh tokens | ❌ |
| `/api/token/refresh/` | POST | Refresh JWT token | ❌ |
| `/api/auth/auth/login/` | POST | User login with email/password | ❌ |
| `/api/auth/auth/register/` | POST | User registration | ❌ |
| `/api/auth/auth/logout/` | POST | User logout (blacklist token) | ✅ |

#### 🏠 Home Services
| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|---------------|
| `/api/services/categories/` | GET/POST | Service categories | ✅ |
| `/api/services/categories/{id}/` | GET/PUT/DELETE | Category details | ✅ |
| `/api/services/services/` | GET/POST | Available services | ✅ |
| `/api/services/services/{id}/` | GET/PUT/DELETE | Service details | ✅ |
| `/api/services/services/by_category/` | GET | Services by category | ✅ |

#### 👤 User Management
| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|---------------|
| `/api/auth/users/` | GET | List users (staff only) | ✅ |
| `/api/auth/users/me/` | GET | Current user profile | ✅ |
| `/api/auth/users/update_profile/` | PUT/PATCH | Update user profile | ✅ |
| `/api/auth/users/change_password/` | POST | Change password | ✅ |

#### 🛠️ System
| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|---------------|
| `/api/auth/health/` | GET | API health check | ❌ |
| `/api/auth/admin/stats/` | GET | User statistics (staff only) | ✅ |
| `/admin/` | GET | Django admin interface | Admin only |

### Security Features

- **JWT Authentication**: Secure token-based authentication
- **Data Encryption**: Sensitive data encryption at rest
- **Input Validation**: Comprehensive request validation
- **Rate Limiting**: API rate limiting for security
- **CORS Configuration**: Proper cross-origin resource sharing
- **SQL Injection Protection**: ORM-based query protection

## 🎨 Frontend (React/Next.js)

### Key Components

- **Authentication Forms**: Login, registration, profile management
- **Service Catalog**: Browse and search services
- **Booking Interface**: Multi-step booking process
- **Provider Profiles**: Detailed provider information
- **Payment Integration**: Secure payment processing
- **Dashboard**: User and provider dashboards
- **Map Integration**: Location-based service discovery

### Features

- **Responsive Design**: Mobile-first responsive interface
- **Real-time Updates**: Live booking status updates
- **Progressive Web App**: PWA capabilities
- **Accessibility**: WCAG compliance
- **Performance**: Optimized loading and caching

## 💾 Database Schema

### Core Models

- **User**: Extended user profiles with home service specific fields
- **Service**: Service definitions and categories
- **Provider**: Service provider profiles and certifications
- **Booking**: Booking records with status tracking
- **Payment**: Payment transactions and billing
- **Review**: User reviews and ratings
- **Notification**: System notifications and communications

## 🚨 Development Status

### ✅ Completed Features

#### 🏗️ Infrastructure & Backend
- **Docker Environment**: Multi-service Docker setup with MySQL, Redis, and Django
- **Database Models**: Complete Django models with UUID primary keys
- **Authentication System**: JWT-based auth with login/register/logout
- **KISS API Design**: Simplified, consistent RESTful endpoints
- **Global Exception Handling**: Unified error handling across all APIs
- **Admin Interface**: Django admin panel for content management

#### 🏠 Home Services Core
- **Service Categories**: Create, read, update, delete service categories
- **Services Management**: Full CRUD operations for home services
- **User Profiles**: Extended user model with home service fields (phone, address)
- **Data Consistency**: All entities use UUID for consistent identification

#### 🔧 Code Quality
- **KISS Principles**: Removed unnecessary abstractions and complexity
- **Standard Django/DRF**: Uses framework best practices, not custom wrappers
- **Clean Architecture**: Eliminated redundant Service layer abstractions
- **Consistent Responses**: Standardized API response formats

### 🔄 Next Development Phase

#### 🚀 Immediate Priorities
- **Service Providers**: Implement provider profiles and availability
- **Booking System**: Create booking workflow and status management
- **Payment Integration**: Add payment processing capabilities
- **Reviews & Ratings**: User feedback and rating system

#### 📱 Frontend Development
- **React/Next.js Application**: Modern frontend interface
- **Mobile Responsive**: Mobile-first design approach
- **Real-time Features**: Live booking updates and notifications

### 🎯 Upcoming Features

- **Advanced Search**: Filter services by location, price, ratings
- **File Uploads**: Service images and provider documents
- **Notification System**: Email/SMS notifications for bookings
- **Admin Dashboard**: Advanced analytics and reporting
- **Automated Testing**: Comprehensive test suite
- **API Documentation**: Interactive API docs with Swagger/OpenAPI
- Deploy to production environment

## 🏃‍♂️ Development Workflow

### Daily Development Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend  # Backend logs
docker-compose logs -f mysql    # Database logs

# Database operations
docker-compose exec backend python manage.py makemigrations
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py shell

# Stop all services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

### Testing the API

```bash
# Test JWT token endpoint
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123456"}'

# Test authenticated endpoint (replace TOKEN with actual token)
curl -X GET http://localhost:8000/api/services/ \
  -H "Authorization: Bearer TOKEN"
```

### Environment Management

The project uses `docker.env` for environment configuration:
- Database credentials
- JWT secret keys
- Debug settings
- CORS origins

## 📚 Documentation

- [API Documentation](./docs/api.md) (Coming Soon)
- [Frontend Components](./docs/components.md) (Coming Soon)
- [Database Schema](./docs/database.md) (Coming Soon)
- [Deployment Guide](./docs/deployment.md) (Coming Soon)

## 🤝 Contributing

This project is currently in active development. Contribution guidelines will be established once the core features are implemented.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**🏠 Building the Future of Home Services! 🔧**