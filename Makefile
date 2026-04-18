.PHONY: install test run up down logs

install:
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f app
