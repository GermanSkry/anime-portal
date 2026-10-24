"""Generate embeddings locally using sentence-transformers"""
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder='./models')

async def generate_embedding(text: str) -> list:
    """Generate embedding for text using sentence-transformers (local, fast)"""
    if not text:
        return [0.0] * 384

    embedding = model.encode(text, convert_to_numpy=True).tolist()
    return embedding[:384]
