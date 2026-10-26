from fastapi import APIRouter
from pydantic import BaseModel
from app.utils.embeddings import generate_embedding

router = APIRouter(prefix="/api", tags=["embeddings"])

class EmbeddingRequest(BaseModel):
    text: str

class EmbeddingResponse(BaseModel):
    embedding: list

@router.post("/embedding")
async def get_embedding(req: EmbeddingRequest):
    """Generate embedding for a query (for semantic similarity matching)"""
    try:
        embedding = await generate_embedding(req.text)
        return EmbeddingResponse(embedding=embedding)
    except Exception as e:
        return {"error": str(e)}
