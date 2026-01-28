from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    # существующие поля...
    id = Column(Integer, primary_key=True)
    pair = Column(String, nullable=False)
    buy_rate = Column(Float, nullable=False)
    sell_rate = Column(Float, nullable=False)
    last_admin_id = Column(BigInteger, nullable=True)
    source = Column(String, nullable=False, default="admin")
    last_updated = Column(DateTime, default=datetime.utcnow)

    # ДОБАВИТЬ ЭТИ ПОЛЯ:
    buy_bank = Column(String, nullable=True)  # Банк для курса покупки
    sell_bank = Column(String, nullable=True)  # Банк для курса продажи