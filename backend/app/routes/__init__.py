"""API route factories."""

from .chat import create_chat_router
from .health import create_health_router
from .portfolio import create_portfolio_router
from .watchlist import create_watchlist_router

__all__ = [
    "create_chat_router",
    "create_health_router",
    "create_portfolio_router",
    "create_watchlist_router",
]
