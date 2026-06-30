import hashlib
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, validator
from pythonjsonlogger import jsonlogger
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

# --- Configuration ---
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL_NAME = os.environ.get("MODEL_NAME", "phi3.5-financial")
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "http://localhost:8080")
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
AUDIT_LOG_PATH = BASE_DIR.parent / "logs" / "interactions_audit.jsonl"

# Clé API — obligatoire au démarrage (R10)
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise RuntimeError(
        "La variable d'environnement API_KEY est requise. Consultez .env.example."
    )

# --- Logging JSON structuré (R9, R29) ---
_log_handler = logging.StreamHandler()
_log_handler.setFormatter(
    jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
)
logger = logging.getLogger("finbot")
logger.addHandler(_log_handler)
logger.setLevel(logging.INFO)

# Patterns de détection (R8, R27)
_BASE64_PATTERN = re.compile(r"[A-Za-z0-9+/]{20,}={0,2}")

# Patterns d'injection à bloquer (R6) — trigger backdoor confirmé
_PROMPT_BLOCKLIST = [
    re.compile(r"J3[\s_]?SU1S[\s_]?UN3[\s_]?P0UP33[\s_]?D3[\s_]?C1R3", re.IGNORECASE),
]

# --- Authentification par clé API (R10) ---
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def _verify_api_key(key: str = Depends(_api_key_header)) -> str:
    if key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Clé API invalide."
        )
    return key


# --- Rate limiting (R22) ---
limiter = Limiter(key_func=get_remote_address)

# --- Application FastAPI ---
app = FastAPI(title="TechCorp Financial Assistant API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS restreint à l'origine autorisée (R22)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


class _RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Journalise chaque requête avec un request_id UUID (R9)."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        t0 = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - t0) * 1000)
        client_ip = request.client.host if request.client else "unknown"
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client_ip_hash": hashlib.sha256(client_ip.encode()).hexdigest()[:16],
                "http_status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


app.add_middleware(_RequestLoggingMiddleware)


# --- Modèles Pydantic (R6, R22) ---
class Message(BaseModel):
    role: str
    content: str = Field(..., max_length=4096)

    @validator("content")
    def _reject_blocked_patterns(cls, v):  # noqa: N805
        for pattern in _PROMPT_BLOCKLIST:
            if pattern.search(v):
                raise ValueError("Contenu rejeté : pattern non autorisé.")
        return v


class ChatRequest(BaseModel):
    messages: List[Message]


# --- Utilitaires de sécurité ---

def _inspect_sse_chunk(line: str, request_id: str) -> None:
    """Détecte les encodages Base64 suspects dans les chunks SSE Ollama (R8, R27)."""
    try:
        data = json.loads(line)
        content = data.get("message", {}).get("content", "")
        m = _BASE64_PATTERN.search(content)
        if m:
            logger.critical(
                "BASE64_DETECTED",
                extra={
                    "request_id": request_id,
                    "match_length": len(m.group()),
                    "offset": m.start(),
                },
            )
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass


def _archive_interaction(
    request_id: str,
    request: Request,
    message_count: int,
    duration_ms: int,
) -> None:
    """Archive les métadonnées d'interaction sans stocker le contenu des messages (R28)."""
    client_ip = request.client.host if request.client else "unknown"
    entry = json.dumps(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id,
            "session_hash": hashlib.sha256(client_ip.encode()).hexdigest()[:16],
            "message_count": message_count,
            "model": MODEL_NAME,
            "duration_ms": duration_ms,
        }
    )
    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except OSError as exc:
        logger.warning("audit_log_write_failed", extra={"error": str(exc)})


# --- Routes ---

@app.get("/", include_in_schema=False)
async def root():
    html = (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")
    html = html.replace("</head>", f'<script>window.__API_KEY__="{API_KEY}";</script></head>', 1)
    return HTMLResponse(html)


@app.get("/api/health")
async def health(_: str = Depends(_verify_api_key)):
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
@limiter.limit("10/minute")
async def chat(
    request: Request,
    chat_req: ChatRequest,
    _: str = Depends(_verify_api_key),
):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    t0 = time.monotonic()

    async def _stream():
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                async with client.stream(
                    "POST",
                    f"{OLLAMA_URL}/api/chat",
                    json={
                        "model": MODEL_NAME,
                        "messages": [
                            {"role": m.role, "content": m.content}
                            for m in chat_req.messages
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
                            _inspect_sse_chunk(line, request_id)
                            yield f"data: {line}\n\n"
        except httpx.ConnectError:
            yield f"data: {json.dumps({'error': 'Impossible de joindre Ollama sur le port 11434.'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            _archive_interaction(
                request_id,
                request,
                len(chat_req.messages),
                int((time.monotonic() - t0) * 1000),
            )
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
