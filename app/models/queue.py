from sqlalchemy import Column, Integer, BigInteger, DateTime, Boolean, String
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class QueueEntry(Base):
    __tablename__ = 'queue_entries'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, nullable=False)
    username = Column(String(100))  # для удобства
    created_at = Column(DateTime, default=datetime.utcnow)
    is_processed = Column(Boolean, default=False)

    def __repr__(self):
        return f"QueueEntry(user_id={self.user_id}, created_at={self.created_at})"
