from fastapi import FastAPI
app = FastAPI(title="Personal OS Embeddings Service", version="0.1.0")

@app.get('/health')
async def health():
    return {'status': 'ok', 'service': 'embeddings', 'mode': 'placeholder'}

@app.post('/api/embed')
async def embed(payload: dict):
    # Placeholder deterministic vector for scaffold testing. Replace with Ollama/Qdrant implementation.
    text = payload.get('text', '')
    seed = sum(ord(c) for c in text) or 1
    vector = [((seed * (i + 1)) % 997) / 997.0 for i in range(16)]
    return {'dim': len(vector), 'vector': vector}
