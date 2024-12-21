.PHONY: up down test build logs clean migrate migrate-test shell dev-services test-services lint format type-check security-check ci-checks test-all test-unit test-integration

# Development Environment
dev-services:
	docker compose up -d db redis

up:
	docker compose up -d db redis
	docker compose up api --build

down:
	docker compose down

# Testing Environment
test:  # Just sets up test environment
	@echo "Setting up test environment..."
	docker compose up -d test-db redis
	@echo "Waiting for test database to be ready..."
	sleep 5
	$(MAKE) migrate-test
	@echo "Test environment ready! Use 'make test-unit' or 'make test-integration' to run tests"

test-all:  # Runs all tests
	docker compose run --rm \
		-e DATABASE_URL="postgresql+asyncpg://keateka:${POSTGRES_PASSWORD}@test-db:5432/keateka_test_db" \
		-e REDIS_URL="redis://redis:6379/1" \
		-e ENVIRONMENT="test" \
		api pytest tests/ -v

test-unit:  # Runs unit tests
	docker compose run --rm \
		-e DATABASE_URL="postgresql+asyncpg://keateka:${POSTGRES_PASSWORD}@test-db:5432/keateka_test_db" \
		-e REDIS_URL="redis://redis:6379/1" \
		-e ENVIRONMENT="test" \
		api pytest tests/unit/ -v

test-integration:  # Runs integration tests
	docker compose run --rm \
		-e DATABASE_URL="postgresql+asyncpg://keateka:${POSTGRES_PASSWORD}@test-db:5432/keateka_test_db" \
		-e REDIS_URL="redis://redis:6379/1" \
		-e ENVIRONMENT="test" \
		api pytest tests/integration/ -v

# Testing Environment
test:
	@echo "Waiting for test database to be ready..."
	docker compose up -d test-db redis
	docker compose logs -f test-db redis

# Shared Commands
build:
	docker compose build

logs:
	docker compose logs -f api

logs-test:
	docker compose logs -f test-db redis

clean:
	docker compose down -v
	docker system prune -f

migrate:
	docker compose run --rm api poetry run alembic upgrade head

migrate-test:
	DATABASE_URL=postgresql+asyncpg://keateka:${POSTGRES_PASSWORD}@test-db:5432/keateka_test_db \
	docker compose run --rm api poetry run alembic upgrade head

shell:
	docker compose exec api /bin/bash

# New commands
lint:
	docker compose run --rm api poetry run flake8 .

format:
	docker compose run --rm api poetry run black .

type-check:
	docker compose run --rm api poetry run mypy .

security-check:
	docker compose run --rm api poetry run bandit -r .

ci-checks: lint format type-check security-check test
