from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

load_dotenv()

# Import routers
from app.routes import anime, characters, stats

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

# Include routers
app.include_router(anime.router)
app.include_router(characters.router)
app.include_router(stats.router)
# TODO: Add more routers
# app.include_router(search.router)
# app.include_router(recommend.router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
