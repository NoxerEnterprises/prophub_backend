.PHONY: install run migrate revision test check-db

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload

migrate:
	alembic upgrade head

revision:
	alembic revision --autogenerate -m "$(m)"

test:
	pytest

check-db:
	python scripts/check_db.py
