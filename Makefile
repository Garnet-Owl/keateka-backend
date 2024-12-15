.PHONY: up down test build logs clean migrate migrate-test shell dev-services test-services

# Development Environment
dev-services:
	docker compose up -d db redis

up:
	docker compose up -d db redis
	docker compose up api --build

down:
	docker compose down

# Testing Environment
test-services:
	docker compose up -d test-db redis
	docker compose logs -f test-db redis

test:
	docker compose up -d test-db redis
	@echo "Waiting for test database to be ready..."
	@sleep 5
	docker compose up test

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
