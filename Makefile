.PHONY: setup migrate dev test schema import lint

VENV = backend/.venv
PYTHON = $(VENV)/bin/python
ALEMBIC = $(VENV)/bin/alembic
HONCHO = $(VENV)/bin/honcho
PYTEST = $(VENV)/bin/pytest
RUFF = $(VENV)/bin/ruff

setup:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r backend/requirements.txt -r backend/requirements-dev.txt
	cd frontend && npm install

migrate:
	cd backend && ../$(PYTHON) -m alembic upgrade head

dev:
	$(PYTHON) -m honcho -f Procfile.dev start

test:
	cd backend && ../$(PYTEST) tests/ -v

schema:
	cd backend && ../$(PYTHON) -m app.cli export-schema

import:
	@if [ -z "$(FILE)" ]; then echo "Usage: make import FILE=path/to/results.json"; exit 1; fi
	cd backend && ../$(PYTHON) -m app.cli import-results --file $(FILE)

lint:
	cd backend && ../$(RUFF) check app tests
