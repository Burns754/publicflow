.PHONY: help install run test clean docker docs

help:
	@echo "PublicFlow - Make Targets"
	@echo "========================="
	@echo "make install    - Install dependencies"
	@echo "make run        - Start backend server"
	@echo "make dev        - Start with auto-reload"
	@echo "make test       - Run tests"
	@echo "make clean      - Clean up cache/temp files"
	@echo "make docker     - Build Docker image"
	@echo "make docker-run - Run Docker container"
	@echo "make lint       - Format & lint code"
	@echo "make docs       - Open API documentation"

install:
	pip install -r requirements.txt

run:
	cd backend && python3 app.py

dev:
	cd backend && uvicorn app:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=backend --cov-report=html

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache htmlcov .coverage
	rm -f publicflow.db-journal

docker:
	docker build -t publicflow:latest .

docker-run:
	docker run -p 8000:8000 -e OPENAI_API_KEY=${OPENAI_API_KEY} publicflow:latest

docker-compose-up:
	docker-compose up

docker-compose-down:
	docker-compose down

lint:
	black backend/
	flake8 backend/ --max-line-length=100
	isort backend/

docs:
	open http://localhost:8000/docs || xdg-open http://localhost:8000/docs

init-db:
	python3 -c "from backend.models import Base, engine; Base.metadata.create_all(bind=engine); print('✅ Database initialized')"

format:
	black backend/ --line-length=100
	isort backend/ --profile=black

requirements-freeze:
	pip freeze > requirements.txt
