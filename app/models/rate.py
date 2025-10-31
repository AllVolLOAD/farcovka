from sqlalchemy import Column, Integer, Float, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class CurrentRate(Base):
    __tablename__ = 'current_rates'

    id = Column(Integer, primary_key=True)
    rate_value = Column(Float, nullable=False, default=0.0)  # например: 95.50
    last_updated = Column(DateTime, default=datetime.utcnow)
    last_admin_id = Column(BigInteger)  # ID админа, который обновил курс

    def __repr__(self):
        return f"CurrentRate(rate={self.rate_value}, updated={self.last_updated})"


class RateHistory(Base):
    __tablename__ = 'rate_history'

    id = Column(Integer, primary_key=True)
    rate_value = Column(Float, nullable=False)
    admin_id = Column(BigInteger)
    user_count = Column(Integer)  # сколько пользователей ждало обновления
    created_at = Column(DateTime, default=datetime.utcnow)
