"""Generate embeddings locally using sentence-transformers"""
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder='./models')

async def generate_embedding(text: str) -> list:
    """Generate embedding for text using sentence-transformers (local, fast)"""
    if not text:
        return [0.0] * 384

    embedding = model.encode(text, convert_to_numpy=True).tolist()
    # the embeddings.plot_embedding column is vector(384); truncating a different model's output
    # would store a broken vector and silently ruin semantic search, so fail instead
    assert len(embedding) == 384, f"model returns {len(embedding)} dims, column is vector(384)"
    return embedding
