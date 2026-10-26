from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from posthog import Posthog

load_dotenv()

# Initialize Sentry for error tracking with logging integration
sentry_dsn = os.getenv("SENTRY_DSN", "")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=os.getenv("ENVIRONMENT", "development"),
        traces_sample_rate=1.0,
        integrations=[
            LoggingIntegration(capture_sentry_logs=True),
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
posthog = Posthog(posthog_api_key, enabled=(posthog_api_key != ""), region=posthog_region)

# Import routers
from app.routes import anime, characters, stats, search, recommend, chat

app = FastAPI(title="Anime Portal API", version="0.1.0")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Anime Portal API - Ready"}

# Include routers (specific routes first, catch-all last)
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
