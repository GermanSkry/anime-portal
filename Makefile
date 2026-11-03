.PHONY: help dev frontend backend db db-up db-down db-reset db-logs kill-all

help:
	@echo "Anime Portal - Development Commands"
	@echo "===================================="
	@echo ""
	@echo "make dev              Start all services (frontend + backend + db)"
	@echo "make frontend         Start React dev server (port 5175)"
	@echo "make backend          Start FastAPI server (port 8000)"
	@echo "make db-up            Start PostgreSQL + Redis containers"
	@echo "make db-down          Stop database containers"
	@echo "make db-reset         Reset database and re-ingest data"
	@echo "make db-logs          Show database container logs"
	@echo "make kill-all         Kill all running services"
	@echo ""

# Start all services
dev: db-up
	@echo "🚀 Starting all services..."
	@make -j2 frontend-bg backend-bg
	@echo "✅ All services running!"
	@echo "   Frontend: http://localhost:5175"
	@echo "   Backend:  http://localhost:8000"
	@echo "   API Docs: http://localhost:8000/docs"

# Frontend only
frontend:
	@echo "🎨 Starting React dev server..."
	cd frontend && npm run dev

frontend-bg:
	@cd frontend && npm run dev > /tmp/frontend.log 2>&1 &
	@echo "✅ Frontend started (logs: /tmp/frontend.log)"

# Backend only
backend:
	@echo "⚙️  Starting FastAPI server..."
	cd backend && source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000

backend-bg:
	@cd backend && source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
	@echo "✅ Backend started (logs: /tmp/backend.log)"

# Database operations
db-up:
	@echo "🐘 Starting PostgreSQL + Redis..."
	@docker-compose up -d 2>/dev/null || echo "⚠️  Docker Compose not found or error - ensure containers are running"
	@echo "✅ Database containers started"

db-down:
	@echo "🛑 Stopping database containers..."
	@docker-compose down 2>/dev/null || echo "⚠️  Docker Compose not found"
	@echo "✅ Database containers stopped"

db-reset:
	@echo "🔄 Resetting database and re-ingesting data..."
	@cd backend && source venv/bin/activate && python3 scripts/update_plots.py
	@cd backend && source venv/bin/activate && python3 scripts/update_trailers.py
	@echo "✅ Database reset complete"

db-logs:
	@docker-compose logs -f 2>/dev/null || echo "⚠️  Docker Compose not found"

# Cleanup
kill-all:
	@echo "💀 Killing all services..."
	@lsof -ti:5175 | xargs kill -9 2>/dev/null || true
	@lsof -ti:8000 | xargs kill -9 2>/dev/null || true
	@echo "✅ All services stopped"

# Development helpers
logs-frontend:
	@tail -f /tmp/frontend.log

logs-backend:
	@tail -f /tmp/backend.log

install-deps:
	@echo "📦 Installing dependencies..."
	@cd frontend && npm install
	@cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
	@echo "✅ Dependencies installed"
