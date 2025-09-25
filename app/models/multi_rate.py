from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class ExchangeRate(Base):
    __tablename__ = 'exchange_rates'

    id = Column(Integer, primary_key=True)
    pair = Column(String(20), nullable=False, unique=True)  # 'RUB/USD', 'USD/USDT'
    rate = Column(Float, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow)
    last_admin_id = Column(BigInteger)

    def __repr__(self):
        return f"ExchangeRate(pair={self.pair}, rate={self.rate})"