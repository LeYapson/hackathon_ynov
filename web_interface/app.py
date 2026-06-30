import httpx
import json
import os
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI(title="TechCorp Financial Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.environ.get("MODEL_NAME", "phi3.5-financial")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]


@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))


@app.get("/api/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
        model_ready = any(MODEL_NAME in m for m in models)
        return {
            "status": "ok",
            "ollama": True,
            "models": models,
            "active_model": MODEL_NAME,
            "model_ready": model_ready,
        }
    except Exception as e:
        return {
            "status": "degraded",
            "ollama": False,
            "error": str(e),
            "active_model": MODEL_NAME,
            "model_ready": False,
        }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    async def stream():
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream(
                    "POST",
                    f"{OLLAMA_URL}/api/chat",
                    json={
                        "model": MODEL_NAME,
                        "messages": [
                            {"role": m.role, "content": m.content}
                            for m in request.messages
                        ],
                        "stream": True,
                    },
                ) as response:
                    if response.status_code != 200:
                        err = await response.aread()
                        yield f"data: {json.dumps({'error': f'Erreur Ollama ({response.status_code}): {err.decode()[:300]}'})}\n\n"
                        return
                    async for line in response.aiter_lines():
                        if line.strip():
                            yield f"data: {line}\n\n"
        except httpx.ConnectError:
            yield f"data: {json.dumps({'error': 'Impossible de joindre Ollama sur le port 11434. Assurez-vous qu il est démarré.'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
