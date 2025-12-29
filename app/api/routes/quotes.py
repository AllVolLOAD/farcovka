"""Exchange rates/quotes routes"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.services.multi_rate_service import MultiRateService


router = APIRouter()


@router.get("/")
async def get_quotes(session: AsyncSession = Depends(get_db)):
    """
    Get current exchange rates from all sources (admin, CBR, RBC).
    Returns structured data with rates from different sources.
    """
    rate_service = MultiRateService(session)
    
    # Get rates by source
    admin_rates = await rate_service.get_rates_by_source("admin")
    cbr_rates = await rate_service.get_rates_by_source("cbr")
    rbc_buy_rates = await rate_service.get_rates_by_source("rbc_buy")
    rbc_sell_rates = await rate_service.get_rates_by_source("rbc_sell")
    
    def format_rate(rate):
        if not rate:
            return None
        return {
            "pair": rate.pair,
            "buy": float(rate.buy_rate),
            "sell": float(rate.sell_rate),
            "last_updated": rate.last_updated.isoformat() if rate.last_updated else None,
            "buy_bank": rate.buy_bank if hasattr(rate, 'buy_bank') else None,
            "sell_bank": rate.sell_bank if hasattr(rate, 'sell_bank') else None
        }
    
    return {
        "admin": [format_rate(r) for r in admin_rates],
        "cbr": [format_rate(r) for r in cbr_rates],
        "rbc_buy": [format_rate(r) for r in rbc_buy_rates],
        "rbc_sell": [format_rate(r) for r in rbc_sell_rates]
    }


@router.get("/{currency_pair}")
async def get_quote_for_pair(
    currency_pair: str,
    session: AsyncSession = Depends(get_db)
):
    """Get exchange rate for specific currency pair (e.g., USD/RUB)"""
    rate_service = MultiRateService(session)
    
    # Get all rates for this pair
    admin_rate = await rate_service.get_rate(currency_pair, source="admin")
    cbr_rate = await rate_service.get_rate(currency_pair, source="cbr")
    rbc_buy_rate = await rate_service.get_rate(currency_pair, source="rbc_buy")
    rbc_sell_rate = await rate_service.get_rate(currency_pair, source="rbc_sell")
    
    def format_rate(rate):
        if not rate:
            return None
        return {
            "buy": float(rate.buy_rate),
            "sell": float(rate.sell_rate),
            "last_updated": rate.last_updated.isoformat() if rate.last_updated else None
        }
    
    return {
        "pair": currency_pair,
        "admin": format_rate(admin_rate),
        "cbr": format_rate(cbr_rate),
        "rbc_buy": format_rate(rbc_buy_rate),
        "rbc_sell": format_rate(rbc_sell_rate)
    }

