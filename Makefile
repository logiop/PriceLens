.PHONY: setup test build backend frontend serve

# One-time setup (create venv + install backend and frontend deps)
setup:
	python3 -m venv backend/.venv
	backend/.venv/bin/pip install -r backend/requirements.txt
	cd frontend && npm install

# Run backend test suite
test:
	cd backend && .venv/bin/python -m pytest

# Build the frontend into frontend/dist (served by FastAPI in production)
build:
	cd frontend && npm run build

# Development: run backend with auto-reload on :8000
backend:
	cd backend && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Development: run Vite dev server on :5173 (proxies /api -> :8000)
frontend:
	cd frontend && npm run dev

# Production: build frontend then serve everything from FastAPI on :8000
serve: build
	cd backend && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
