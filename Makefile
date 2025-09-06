# Windows Log Gathering Agent - Docker Management

.PHONY: help build up down logs clean dev prod test

# Default target
help: ## Show this help message
	@echo "Windows Log Gathering Agent - Docker Management"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development targets
dev: ## Start development environment with hot reload
	docker-compose -f docker-compose.dev.yml up -d
	@echo "Development environment started!"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend: http://localhost:8000"

dev-build: ## Build and start development environment
	docker-compose -f docker-compose.dev.yml build
	docker-compose -f docker-compose.dev.yml up -d

dev-logs: ## View development logs
	docker-compose -f docker-compose.dev.yml logs -f

dev-stop: ## Stop development environment
	docker-compose -f docker-compose.dev.yml down

# Production targets
prod: ## Start production environment
	docker-compose up -d
	@echo "Production environment started!"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend: http://localhost:8000"

prod-build: ## Build and start production environment
	docker-compose build
	docker-compose up -d

# General targets
build: ## Build all containers
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## View logs from all services
	docker-compose logs -f

logs-backend: ## View backend logs
	docker-compose logs -f backend

logs-frontend: ## View frontend logs
	docker-compose logs -f frontend

ps: ## Show running containers
	docker-compose ps

# Health checks
health: ## Check service health
	@echo "Checking service health..."
	@curl -f http://localhost:8000/health || echo "Backend health check failed"
	@curl -f http://localhost:3000/ > /dev/null 2>&1 && echo "Frontend is healthy" || echo "Frontend health check failed"
	@docker-compose exec -T redis redis-cli ping > /dev/null 2>&1 && echo "Redis is healthy" || echo "Redis health check failed"

status: ## Show detailed service status
	@echo "=== Service Status ==="
	docker-compose ps
	@echo ""
	@echo "=== Resource Usage ==="
	docker stats --no-stream

# Maintenance targets
clean: ## Clean up containers, images, and volumes
	docker-compose down -v
	docker system prune -f
	docker volume prune -f

clean-all: ## Clean everything including images
	docker-compose down -v --rmi all
	docker system prune -af
	docker volume prune -f

update: ## Update and restart services
	docker-compose pull
	docker-compose up -d

# Database targets (if implemented)
db-backup: ## Backup database data
	docker run --rm -v log-agent-data:/data -v $(PWD):/backup alpine tar czf /backup/data-backup-$(shell date +%Y%m%d-%H%M%S).tar.gz /data
	@echo "Database backup created"

db-restore: ## Restore database from backup (specify BACKUP_FILE)
	@test -n "$(BACKUP_FILE)" || (echo "Please specify BACKUP_FILE=filename"; exit 1)
	docker run --rm -v log-agent-data:/data -v $(PWD):/backup alpine tar xzf /backup/$(BACKUP_FILE) -C /
	@echo "Database restored from $(BACKUP_FILE)"

# Development utilities
shell-backend: ## Open shell in backend container
	docker-compose exec backend bash

shell-frontend: ## Open shell in frontend container
	docker-compose exec frontend sh

shell-redis: ## Open Redis CLI
	docker-compose exec redis redis-cli

# Testing targets
test: ## Run tests in containers
	docker-compose -f docker-compose.dev.yml exec backend python -m pytest
	docker-compose -f docker-compose.dev.yml exec frontend npm test

test-build: ## Build test environment
	docker-compose -f docker-compose.dev.yml build
	docker-compose -f docker-compose.dev.yml run --rm backend python -m pytest

# Quick setup targets
setup: ## Initial setup - copy env file and start development
	cp .env.example .env
	@echo "Please edit .env file with your configuration"
	@echo "Then run: make dev"

quick-start: ## Quick start for development (assumes .env exists)
	make dev
	@echo "Waiting for services to start..."
	@sleep 10
	make health

# Docker maintenance
docker-clean: ## Clean Docker system
	docker system prune -f
	docker image prune -f
	docker volume prune -f

docker-reset: ## Reset Docker completely (WARNING: removes everything)
	docker system prune -af --volumes
	docker network prune -f