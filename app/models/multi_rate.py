from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

from sqlalchemy import Column, String, Float, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id = Column(Integer, primary_key=True, index=True)
    pair = Column(String, unique=True, index=True)  # Например: "USD/RUB"
    buy_rate = Column(Float, nullable=False)  # Курс покупки
    sell_rate = Column(Float, nullable=False)  # Курс продажи
    last_updated = Column(DateTime, default=datetime.utcnow)
    last_admin_id = Column(BigInteger)  # ID админа, обновившего курс
