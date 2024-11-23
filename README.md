# KeaTeka Backend

KeaTeka is a cleaning service marketplace application designed for the Nairobi market, connecting cleaners with clients through a user-friendly platform that handles scheduling, payments, and service management.

## Features

- 🔐 User Authentication & Authorization
- 📅 Job Scheduling & Management
- 💰 M-PESA Integration
- 🤝 Cleaner-Client Matching System
- ⭐ Review & Rating System
- 📱 Real-time Notifications
- 📍 Location-based Services

## Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Authentication:** JWT
- **Payment:** M-PESA
- **Push Notifications:** Firebase Cloud Messaging
- **Task Queue:** Celery (with Redis)
- **Testing:** Pytest
- **Documentation:** OpenAPI/Swagger

## Prerequisites

- Python 3.12.6 or higher
- Poetry for dependency management
- PostgreSQL 14+
- Redis (for caching and task queue)
- Firebase Admin SDK credentials
- M-PESA API credentials

## Getting Started

1. **Clone the repository**
```bash
git clone https://github.com/your-org/keateka-backend.git
cd keateka-backend
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
poetry run python -m uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Alternative API docs: `http://localhost:8000/redoc`

## Development

### Project Structure
```
keateka-backend/
├── app/
│   ├── api/            # API endpoints
│   ├── core/           # Core functionality
│   ├── models/         # SQLAlchemy models
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # Business logic
│   └── utils/          # Utility functions
├── tests/              # Test files
├── migrations/         # Alembic migrations
└── docs/              # Documentation
```

### Running Tests
```bash
# Run all tests
poetry run pytest

# Run tests with coverage report
poetry run pytest --cov=app tests/

# Run specific test file
poetry run pytest tests/test_specific_file.py
```

### Code Quality
```bash
# Format code
poetry run black .

# Run linter
poetry run ruff check .

# Type checking
poetry run mypy app
```

### Database Migrations

```bash
# Create a new migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback last migration
poetry run alembic downgrade -1

# Show migration history
poetry run alembic history
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

### Payments
- POST `/api/v1/payments/initiate` - Initiate M-PESA payment
- POST `/api/v1/payments/confirm` - Confirm payment
- GET `/api/v1/payments/status/{payment_id}` - Check payment status

For complete API documentation, visit `/docs` endpoint after running the server.

## Deployment

### Using Docker
```bash
# Build the image
docker build -t keateka-backend .

# Run the container
docker run -p 8000:8000 keateka-backend
```

### Using Docker Compose
```bash
docker-compose up --build
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql://user:pass@localhost:5432/keateka` |
| `SECRET_KEY` | JWT secret key | Required |
| `MPESA_CONSUMER_KEY` | M-PESA API consumer key | Required |
| `MPESA_CONSUMER_SECRET` | M-PESA API consumer secret | Required |
| `FIREBASE_CREDENTIALS_PATH` | Path to Firebase credentials JSON | Required |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please make sure to update tests as appropriate.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

- Project Link: [https://github.com/Garnet-Owl/keateka-backend](https://github.com/Garnet-Owl/keateka-backend)
- Documentation: [https://docs.keateka.com](https://docs.keateka.com)
- Support: [support@keateka.com](mailto:support@keateka.com)


![img.png](img.png)
