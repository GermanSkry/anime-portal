"""Generate embeddings via Claude API"""
from anthropic import Anthropic
import os

client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

async def generate_embedding(text: str) -> list:
    """Generate embedding for text using Claude API"""
    if not text:
        return [0.0] * 1024

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        system="Convert the following text to a compact semantic representation. Return a JSON array of 1024 floats between -1 and 1 representing the embedding. Return ONLY the JSON array, no other text.",
        messages=[{"role": "user", "content": text}]
    )

    try:
        embedding_text = response.content[0].text.strip()
        # Parse JSON array from response
        import json
        embedding = json.loads(embedding_text)
        # Normalize if needed
        if len(embedding) != 1024:
            embedding = embedding[:1024] + [0.0] * (1024 - len(embedding))
        return embedding[:1024]
    except Exception as e:
        print(f"Error parsing embedding: {e}")
        return [0.0] * 1024
