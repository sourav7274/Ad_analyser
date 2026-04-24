.PHONY: install run test build up

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest tests/

build:
	docker build -t ad-analyser .

up:
	docker-compose up
