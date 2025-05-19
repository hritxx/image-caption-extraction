.PHONY: setup install test clean run run-api run-batch docker-build docker-up docker-down lint format help init-db diagnose entity-test search

# Default target
help:
	@echo "Paper Extractor - Makefile commands:"
	@echo "--------------------------------"
	@echo "setup      - Create virtual environment and install dependencies"
	@echo "install    - Install dependencies only"
	@echo "test       - Run tests"
	@echo "entity-test- Run entity extraction tests"
	@echo "run-api    - Run the API server"
	@echo "run-batch  - Run the batch processor"
	@echo "init-db    - Initialize the database"
	@echo "docker-build - Build the Docker images"
	@echo "docker-up  - Start the Docker containers"
	@echo "docker-down- Stop the Docker containers"
	@echo "clean      - Remove temporary files and artifacts"
	@echo "lint       - Run code linting"
	@echo "format     - Format code with black"
	@echo "diagnose   - Run system diagnostics"
	@echo "search     - Search PubMed for a query"

# Setup virtual environment and install dependencies
setup:
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

# Install dependencies
install:
	pip install -r requirements.txt

# Run tests
test:
	pytest

# Run entity extraction tests
entity-test:
	python test_entity_extraction.py

# Run the API server
run-api:
	uvicorn api:app --reload

# Run the batch processor
run-batch:
	python batch_processor.py

# Initialize the database
init-db:
	python init_db.py

# Build Docker images
docker-build:
	docker-compose build

# Start Docker containers
docker-up:
	docker-compose up -d

# Stop Docker containers
docker-down:
	docker-compose down

# Run system diagnostics
diagnose:
	python main_cli.py --diagnose

# Search PubMed
search:
	@read -p "Enter search query: " query; \
	python main_cli.py --search "$$query"

# Clean temporary files
clean:
	rm -rf __pycache__/
	rm -rf *.pyc
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/

# Run linting
lint:
	flake8 .
	pylint *.py

# Format code
format:
	black .
