from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import Settings
from app.models import ToolRequest
from app.security import RateLimiter, audit, verify_token
from app.tools import ToolContext, build_registry

settings = Settings.from_env()
registry = build_registry()
context = ToolContext(settings)
limiter = RateLimiter()
strict_limiter = RateLimiter(limit=5)
boot_time = time.monotonic()


def load_token() -> str:
    try:
        return settings.token_file.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


async def authenticate(authorization: str | None = Header(default=None)) -> None:
    token = (
        authorization.removeprefix("Bearer ")
        if authorization and authorization.startswith("Bearer ")
        else None
    )
    if not verify_token(token, load_token()):
        raise HTTPException(status_code=401, detail="Unauthorized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Secure Windows Execution Agent", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def protect_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    if request.url.path not in {"/health", "/openapi.json", "/docs", "/redoc"}:
        client = request.client.host if request.client else "unknown"
        if not limiter.allow(client):
            audit(settings.audit_log, request.url.path, "rate_limited", request_id)
            return JSONResponse(
                status_code=429, content={"detail": "Rate limit exceeded", "request_id": request_id}
            )
        raw_length = request.headers.get("content-length")
        if request.method == "POST" and not raw_length:
            return JSONResponse(
                status_code=411,
                content={"detail": "Content-Length is required", "request_id": request_id},
            )
        try:
            content_length = int(raw_length or 0)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid Content-Length", "request_id": request_id},
            )
        if content_length < 0 or content_length > settings.max_request_bytes:
            return JSONResponse(
                status_code=413, content={"detail": "Request too large", "request_id": request_id}
            )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health", dependencies=[Depends(authenticate)])
def health() -> dict:
    return {"status": "healthy", "agent": "running"}


@app.get("/status", dependencies=[Depends(authenticate)])
def status() -> dict:
    from app.tools import _vscode

    return {
        "agent": "running",
        "version": app.version,
        "uptime_seconds": int(time.monotonic() - boot_time),
        "omniroute": context.omniroute_status(),
        "vscode": _vscode(context),
    }


@app.get("/tools", dependencies=[Depends(authenticate)])
def tools() -> dict:
    return {"tools": registry.schemas()}


@app.post("/tools/call", dependencies=[Depends(authenticate)])
def call_tool(payload: ToolRequest, request: Request) -> dict:
    request_id = request.state.request_id
    if payload.name in {
        "git.clone",
        "omniroute.install",
        "omniroute.configure",
        "omniroute.start",
        "omniroute.restart",
        "secret.set",
        "vscode.extension.install",
        "scheduler.create",
        "scheduler.remove",
    }:
        client = request.client.host if request.client else "unknown"
        if not strict_limiter.allow(client):
            audit(settings.audit_log, payload.name, "strict_rate_limited", request_id)
            return JSONResponse(
                status_code=429,
                content={"detail": "Operation rate limit exceeded", "request_id": request_id},
            )
    try:
        result = registry.invoke(payload.name, payload.arguments, context)
        audit(settings.audit_log, payload.name, "success", request_id)
        return {"success": True, "tool": payload.name, "result": result, "request_id": request_id}
    except KeyError:
        audit(settings.audit_log, payload.name, "denied", request_id)
        raise HTTPException(
            status_code=404, detail={"code": "UNKNOWN_TOOL", "request_id": request_id}
        ) from None
    except Exception:
        audit(settings.audit_log, payload.name, "failed", request_id)
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Operation failed", "request_id": request_id},
        )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Never echo submitted values: invalid requests can contain credentials.
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Invalid request",
            "request_id": getattr(request.state, "request_id", "unknown"),
        },
    )
