# Wildfire Intelligence Platform - Data Storage Service
# Makefile for development and deployment tasks

# Variables
PYTHON = python3
PIP = pip3
SERVICE_NAME = data-storage-service
DOCKER_IMAGE = wildfire/data-storage-service
DOCKER_TAG = latest

# Colors for output
BLUE = \033[0;34m
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

.PHONY: help install install-dev test test-unit test-integration lint format type-check clean build run docker-build docker-run docker-push deploy health-check logs

# Default target
help: ## Show this help message
	@echo "$(BLUE)Wildfire Intelligence Platform - Data Storage Service$(NC)"
	@echo "$(BLUE)Available commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development setup
install: ## Install production dependencies
	@echo "$(YELLOW)Installing production dependencies...$(NC)"
	$(PIP) install -r requirements.txt

install-dev: ## Install development dependencies
	@echo "$(YELLOW)Installing development dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-asyncio pytest-cov black flake8 mypy

# Code quality
lint: ## Run code linting
	@echo "$(YELLOW)Running flake8 linting...$(NC)"
	flake8 src/ tests/ --max-line-length=120 --extend-ignore=E203,W503

format: ## Format code with black
	@echo "$(YELLOW)Formatting code with black...$(NC)"
	black src/ tests/ --line-length=120

format-check: ## Check code formatting
	@echo "$(YELLOW)Checking code formatting...$(NC)"
	black --check src/ tests/ --line-length=120

type-check: ## Run type checking with mypy
	@echo "$(YELLOW)Running type checking...$(NC)"
	mypy src/ --ignore-missing-imports

# Testing
test: ## Run all tests
	@echo "$(YELLOW)Running all tests...$(NC)"
	pytest tests/ -v

test-unit: ## Run unit tests only
	@echo "$(YELLOW)Running unit tests...$(NC)"
	pytest tests/unit/ -v -m "not slow"

test-integration: ## Run integration tests only
	@echo "$(YELLOW)Running integration tests...$(NC)"
	pytest tests/integration/ -v

test-performance: ## Run performance tests
	@echo "$(YELLOW)Running performance tests...$(NC)"
	pytest tests/ -v -m "performance"

test-coverage: ## Run tests with coverage report
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# Development server
run: ## Run development server
	@echo "$(YELLOW)Starting development server...$(NC)"
	uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload

run-prod: ## Run production server
	@echo "$(YELLOW)Starting production server...$(NC)"
	uvicorn src.main:app --host 0.0.0.0 --port 8001 --workers 4

# Docker operations
docker-build: ## Build Docker image
	@echo "$(YELLOW)Building Docker image...$(NC)"
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

docker-run: ## Run Docker container
	@echo "$(YELLOW)Running Docker container...$(NC)"
	docker run -p 8001:8001 --env-file .env $(DOCKER_IMAGE):$(DOCKER_TAG)

docker-push: ## Push Docker image to registry
	@echo "$(YELLOW)Pushing Docker image...$(NC)"
	docker push $(DOCKER_IMAGE):$(DOCKER_TAG)

docker-compose-up: ## Start services with docker-compose
	@echo "$(YELLOW)Starting services with docker-compose...$(NC)"
	docker-compose up -d

docker-compose-down: ## Stop services with docker-compose
	@echo "$(YELLOW)Stopping services with docker-compose...$(NC)"
	docker-compose down

# Database operations
db-migrate: ## Run database migrations
	@echo "$(YELLOW)Running database migrations...$(NC)"
	alembic upgrade head

db-migration: ## Create new database migration
	@echo "$(YELLOW)Creating new migration...$(NC)"
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

db-reset: ## Reset database (WARNING: destroys data)
	@echo "$(RED)WARNING: This will destroy all data!$(NC)"
	@read -p "Are you sure? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		alembic downgrade base && alembic upgrade head; \
	fi

# Health and monitoring
health-check: ## Check service health
	@echo "$(YELLOW)Checking service health...$(NC)"
	curl -f http://localhost:8001/health || echo "$(RED)Service is not healthy$(NC)"

metrics: ## View service metrics
	@echo "$(YELLOW)Fetching service metrics...$(NC)"
	curl -s http://localhost:8001/metrics

logs: ## View service logs (requires Docker)
	@echo "$(YELLOW)Viewing service logs...$(NC)"
	docker logs -f $(SERVICE_NAME) 2>/dev/null || echo "$(RED)Container not running$(NC)"

# Cleanup
clean: ## Clean temporary files
	@echo "$(YELLOW)Cleaning temporary files...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info

clean-docker: ## Clean Docker images and containers
	@echo "$(YELLOW)Cleaning Docker resources...$(NC)"
	docker system prune -f
	docker volume prune -f

# Security
security-scan: ## Run security vulnerability scan
	@echo "$(YELLOW)Running security scan...$(NC)"
	safety check --json || echo "$(RED)Security vulnerabilities found$(NC)"

# Documentation
docs: ## Generate documentation
	@echo "$(YELLOW)Generating documentation...$(NC)"
	@echo "Documentation generation not implemented yet"

# Load testing
load-test: ## Run load tests (requires locust)
	@echo "$(YELLOW)Running load tests...$(NC)"
	@echo "Load testing not implemented yet"

# Deployment
deploy-dev: ## Deploy to development environment
	@echo "$(YELLOW)Deploying to development...$(NC)"
	@echo "Development deployment not implemented yet"

deploy-prod: ## Deploy to production environment
	@echo "$(YELLOW)Deploying to production...$(NC)"
	@echo "Production deployment not implemented yet"

# Utilities
requirements: ## Update requirements.txt from current environment
	@echo "$(YELLOW)Updating requirements.txt...$(NC)"
	$(PIP) freeze > requirements.txt

check-env: ## Check environment configuration
	@echo "$(YELLOW)Checking environment configuration...$(NC)"
	@echo "Python version: $$($(PYTHON) --version)"
	@echo "Pip version: $$($(PIP) --version)"
	@echo "Service name: $(SERVICE_NAME)"
	@echo "Docker image: $(DOCKER_IMAGE):$(DOCKER_TAG)"

# Quick development workflow
dev: install-dev lint type-check test ## Full development workflow: install, lint, type-check, test

# CI/CD pipeline simulation
ci: clean install lint type-check test-coverage ## Simulate CI pipeline

# Production readiness check
prod-check: clean install lint type-check test-coverage security-scan ## Full production readiness check