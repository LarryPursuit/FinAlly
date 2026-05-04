"""Chat API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.db.database import Database
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource
from app.services.chat import process_chat_message
from app.services.llm import LLMClient, LLMError

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


def create_chat_router(
    db: Database,
    price_cache: PriceCache,
    market_data_source: MarketDataSource,
    llm_client: LLMClient,
) -> APIRouter:
    """Create the chat router with injected dependencies."""
    router = APIRouter(prefix="/api", tags=["chat"])

    @router.post("/chat")
    async def post_chat(request: ChatRequest) -> JSONResponse:
        """Send a chat message and receive AI response with executed actions."""
        try:
            result = await process_chat_message(
                db, price_cache, market_data_source, llm_client,
                request.message.strip(),
            )
            return JSONResponse(status_code=200, content=result)
        except LLMError:
            return JSONResponse(
                status_code=500,
                content={"error": "LLM service unavailable", "code": "LLM_ERROR"},
            )
        except Exception:
            logger.exception("Unexpected error in chat")
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error", "code": "INTERNAL_ERROR"},
            )

    return router
