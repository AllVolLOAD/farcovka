"""FastAPI application setup"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, auth, orders, quotes, walletconnect


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="FarCovka API",
        version="1.0.0",
        description="API for FarCovka Telegram bot - exchange and wallet management"
    )
    
    # CORS middleware (adjust origins in production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    app.include_router(quotes.router, prefix="/quotes", tags=["Quotes"])
    app.include_router(orders.router, prefix="/orders", tags=["Orders"])
    app.include_router(walletconnect.router, prefix="/wc", tags=["WalletConnect"])
    app.include_router(admin.router)
    
    @app.get("/")
    async def root():
        return {
            "message": "FarCovka API",
            "version": "1.0.0",
            "docs": "/docs"
        }
    
    @app.get("/health")
    async def health():
        return {"status": "ok"}
    
    return app

