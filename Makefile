.PHONY: help dev frontend backend db db-up db-down db-reset db-logs kill-all kafka-logs kafka-topics kafka-test go-service

help:
	@echo "Anime Portal - Development Commands"
	@echo "===================================="
	@echo ""
	@echo "make dev              Start all services (frontend + backend + db)"
	@echo "make frontend         Start React dev server (port 5175)"
	@echo "make backend          Start FastAPI server (port 8000)"
	@echo "make go-service       Start Go search service + Kafka consumers (port 8001)"
	@echo "make db-up            Start PostgreSQL + Redis + Kafka containers"
	@echo "make db-down          Stop database containers"
	@echo "make db-reset         Reset database and re-ingest data"
	@echo "make db-logs          Show database container logs"
	@echo "make kafka-topics     List Kafka topics"
	@echo "make kafka-test       Test Kafka by sending a chat message"
	@echo "make kafka-logs       Show Kafka broker logs"
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

# Go service with Kafka consumers
go-service:
	@echo "🚀 Starting Go search service + Kafka consumers..."
	@cd go-search && go run main.go

# Kafka operations
kafka-topics:
	@echo "📋 Kafka Topics:"
	@docker exec anime_kafka rpk topic list

kafka-logs:
	@docker logs -f anime_kafka

kafka-test:
	@echo "📨 Testing Kafka - sending chat message..."
	@curl -X POST http://localhost:8000/api/chat \
		-H "Content-Type: application/json" \
		-d '{"message": "recommend action anime", "history": []}' \
		-s | jq '.'
	@echo ""
	@echo "⏳ Waiting 2s for consumers to process..."
	@sleep 2
	@echo ""
	@echo "📊 Chat history (saved by DB consumer):"
	@curl -s http://localhost:8000/api/chat/history | jq '.[-1]'
	@echo ""
	@echo "📋 Kafka topic status:"
	@docker exec anime_kafka rpk topic info chat.messages 2>/dev/null || echo "Checking messages..."
