"""HTTP/SSE transport wrapper — exposes jw-org-mcp over HTTP for Claude.ai."""

import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from .server import app as mcp_app, cleanup
from .config import settings

logger = logging.getLogger(__name__)


# ── SSE transport ──────────────────────────────────────────────────────────────

sse_transport = SseServerTransport("/messages/")


async def handle_sse(request: Request) -> Response:
    """SSE endpoint — Claude.ai connects here to receive events."""
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_app.run(
            streams[0],
            streams[1],
            mcp_app.create_initialization_options(),
        )
    return Response()


async def handle_messages(request: Request) -> Response:
    """POST endpoint — Claude.ai sends tool calls here."""
    await sse_transport.handle_post_message(
        request.scope, request.receive, request._send
    )
    return Response()


# ── Health / info endpoints ────────────────────────────────────────────────────

async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "jw-org-mcp"})


async def info(request: Request) -> JSONResponse:
    return JSONResponse({
        "name": "jw-org-mcp",
        "description": "Verified access to jw.org content",
        "tools": ["search_content", "get_article", "get_scripture", "get_cache_stats"],
        "transport": "SSE",
        "mcp_endpoint": "/sse",
    })


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app):
    logger.info("jw-org-mcp HTTP server starting up")
    yield
    logger.info("jw-org-mcp HTTP server shutting down")
    await cleanup()


# ── Starlette app ──────────────────────────────────────────────────────────────

starlette_app = Starlette(
    lifespan=lifespan,
    routes=[
        Route("/health", health, methods=["GET"]),
        Route("/info",   info,   methods=["GET"]),
        Route("/sse",    handle_sse, methods=["GET"]),
        Mount("/messages/", app=sse_transport.handle_post_message),
    ],
)


# ── Entry point ────────────────────────────────────────────────────────────────

def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
    )
    logger.info(f"Starting HTTP/SSE server on {host}:{port}")
    logger.info(f"MCP SSE endpoint: http://{host}:{port}/sse")
    uvicorn.run(starlette_app, host=host, port=port)


if __name__ == "__main__":
    serve()
