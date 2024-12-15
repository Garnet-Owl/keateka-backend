# KeaTeka Backend

KeaTeka is a cleaning service marketplace application designed for the Nairobi market, connecting cleaners with clients through a user-friendly platform that handles scheduling, payments, and service management.

## Features

- 🔐 **Authentication & Authorization**: Secure JWT-based authentication system
- 📅 **Job Management**:
  - Sophisticated scheduling system
  - Real-time time tracking
  - Automated cleaner-client matching
- 💰 **Payments**: Integrated M-PESA payment processing
- 📍 **Location Services**:
  - Real-time location tracking
  - Route optimization
  - ETA calculations
- 📱 **Real-time Features**:
  - WebSocket-based time tracking
  - Live notifications
  - Real-time location updates
- ⭐ **Reviews & Ratings**: Comprehensive rating system for both cleaners and clients

## Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL 14+
- **Cache & Queue:** Redis 7
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Authentication:** JWT
- **Payment:** M-PESA API
- **Notifications:** Firebase Cloud Messaging
- **Maps:** Google Maps API
- **Testing:** Pytest
- **Documentation:** OpenAPI/Swagger
- **Type Checking:** MyPy
- **Linting:** Ruff, Black, Flake8
- **Containerization:** Docker & Docker Compose

## Prerequisites

- Docker & Docker Compose
- Make (optional, for using Makefile commands)
- Firebase Admin SDK credentials
- M-PESA API credentials
- Google Maps API key

## Project Structure

```
keateka-backend/
├── app/
│   ├── features/               # Feature modules
│   │   ├── auth/              # Authentication
│   │   ├── jobs/              # Job management
│   │   ├── location/          # Location services
│   │   ├── payments/          # Payment processing
│   │   ├── reviews/           # Rating system
│   │   ├── notifications/     # Push notifications
│   │   └── websockets/        # Real-time communication
│   │
│   ├── shared/                # Shared utilities
│   │   ├── middleware/        # Custom middleware
│   │   └── utils/            # Shared utilities
│   │
│   └── main.py               # Application entry
│
├── tests/
│   ├── integration/          # Integration tests
│   └── unit/                # Unit tests
│
└── config files...          # Various configuration files
```

## Getting Started with Docker

1. **Clone the repository**
```bash
git clone https://github.com/Garnet-Owl/keateka-backend.git
cd keateka-backend
```

2. **Create environment file**
```bash
cp .env.example .env
```
Add the following required variables to `.env`:
```
POSTGRES_PASSWORD=your_secure_password_here
```

3. **Development Setup**
```bash
# Start services and show API logs
make up

# Or start only DB and Redis in background
make dev-services
```

4. **Run database migrations**
```bash
make migrate      # For main database
make migrate-test # For test database
```

5. **Testing Setup**
```bash
# Run tests with logs
make test

# Or start only test services in background
make test-services
```

The API will be available at:
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Alternative API docs: http://localhost:8000/redoc

Database access:
- Main DB: localhost:5432 (keateka_db)
- Test DB: localhost:5433 (keateka_test_db)

### Additional Docker Commands

```bash
# Stop all services
make down

# View specific logs
make logs        # View API logs
make logs-test   # View test database logs

# Start specific services
make dev-services   # Start DB and Redis for development
make test-services  # Start test-DB and Redis for testing

# Rebuild containers
make build

# Clean up volumes and containers
make clean

# Access container shell
make shell
```

## Alternative Setup (Local Development)

If you prefer to run services locally without Docker:

1. **Install Poetry**
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. **Install dependencies**
```bash
poetry install
```

3. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Initialize the database**
```bash
poetry run alembic upgrade head
```

5. **Run the development server**
```bash
poetry run uvicorn app.main:app --reload
```

## Development

### Code Quality Tools

```bash
# Format code
poetry run black .

# Run linter
poetry run ruff check .

# Type checking
poetry run mypy app

# Run pre-commit hooks
poetry run pre-commit run --all-files
```

### Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=term-missing

# Run specific feature tests
poetry run pytest tests/integration/test_jobs.py
```

### Database Migrations

```bash
# Create migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback
poetry run alembic downgrade -1
```

## API Documentation

### Authentication
- POST `/api/v1/auth/register` - Register new user
- POST `/api/v1/auth/login` - User login
- POST `/api/v1/auth/refresh` - Refresh access token

### Jobs
- POST `/api/v1/jobs` - Create new job
- GET `/api/v1/jobs` - List jobs
- GET `/api/v1/jobs/{job_id}` - Get job details
- PUT `/api/v1/jobs/{job_id}` - Update job
- DELETE `/api/v1/jobs/{job_id}` - Cancel job
- WS `/api/v1/jobs/{job_id}/track` - Real-time time tracking

### Location
- POST `/api/v1/location/update` - Update location
- GET `/api/v1/location/route` - Get optimal route
- GET `/api/v1/location/eta` - Get ETA

### Payments
- POST `/api/v1/payments/initiate` - Initiate M-PESA payment
- POST `/api/v1/payments/confirm` - Confirm payment
- GET `/api/v1/payments/status/{payment_id}` - Check payment status

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `POSTGRES_PASSWORD` | PostgreSQL password | Yes | - |
| `DATABASE_URL` | PostgreSQL connection URL | Yes | `postgresql://keateka:keateka123@localhost:5432/keateka_db` |
| `REDIS_URL` | Redis connection URL | Yes | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT secret key | Yes | - |
| `MPESA_CONSUMER_KEY` | M-PESA API consumer key | Yes | - |
| `MPESA_CONSUMER_SECRET` | M-PESA API consumer secret | Yes | - |
| `FIREBASE_CREDENTIALS_PATH` | Path to Firebase credentials | Yes | - |
| `GOOGLE_MAPS_API_KEY` | Google Maps API key | Yes | - |

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`make test` or `poetry run pytest`)
4. Commit changes (`git commit -m 'feat(module): add some feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

Please ensure:
- All tests pass
- Code is formatted with Black
- Type hints are added
- Documentation is updated
- Pre-commit hooks pass

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- GitHub Issues: [https://github.com/Garnet-Owl/keateka-backend/issues](https://github.com/Garnet-Owl/keateka-backend/issues)
- Documentation: [https://docs.keateka.com](https://docs.keateka.com)
- Support: [support@keateka.com](mailto:support@keateka.com)
