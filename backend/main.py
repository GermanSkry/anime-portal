from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from posthog import Posthog
from app.utils.langfuse_tracer import get_dashboard_url, flush_traces

load_dotenv()

# Initialize Sentry for error tracking with logging integration
sentry_dsn = os.getenv("SENTRY_DSN", "")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=os.getenv("ENVIRONMENT", "development"),
        traces_sample_rate=1.0,
        integrations=[
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
    )

# Configure logging to send to Sentry
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize PostHog for analytics
posthog_api_key = os.getenv("POSTHOG_API_KEY", "")
posthog_region = os.getenv("POSTHOG_REGION", "us")
if posthog_api_key:
    posthog = Posthog(
        posthog_api_key,
        host="https://eu.i.posthog.com" if posthog_region == "eu" else "https://us.i.posthog.com"
    )
else:
    posthog = None

# Import routers
from app.routes import anime, characters, stats, search, recommend, chat, embeddings

app = FastAPI(title="Anime Portal API", version="0.1.0")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize observability and Kafka on startup"""
    logging.info("🚀 Anime Portal API Starting")
    logging.info(f"📊 Langfuse Dashboard: {get_dashboard_url()}")

    # Initialize Kafka producer (lazy loads on first use)
    from app.routes.chat import get_kafka_producer
    try:
        producer = await get_kafka_producer()
        logging.info("✅ Kafka producer initialized")
    except Exception as e:
        logging.warning(f"⚠️ Kafka not available: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Flush observability traces and close Kafka on shutdown"""
    logging.info("🛑 Shutting down - flushing traces")
    flush_traces()

    from app.routes.chat import close_kafka_producer
    await close_kafka_producer()
    logging.info("✅ Kafka producer closed")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Anime Portal API - Ready"}

@app.get("/observability")
async def observability():
    """Get observability dashboard URLs and status"""
    return {
        "status": "ok",
        "dashboards": {
            "langfuse": get_dashboard_url(),
            "docs": "http://localhost:8000/docs"
        },
        "tracing": {
            "enabled": bool(os.getenv("LANGFUSE_PUBLIC_KEY")),
            "host": os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        }
    }

# Include routers (specific routes first, catch-all last)
app.include_router(embeddings.router)
app.include_router(chat.router)
app.include_router(search.router)
app.include_router(recommend.router)
app.include_router(stats.router)
app.include_router(characters.router)
app.include_router(anime.router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
