"""Database models for predictions."""

from sqlalchemy import Column, Integer, Float, String, DateTime, JSON, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()


class Prediction(Base):
    __tablename__ = 'predictions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    features = Column(JSON, nullable=False)

    predicted_price = Column(Float, nullable=False)

    model_name = Column(String(100), nullable=True, index=True)
    model_version = Column(String(50), nullable=True, index=True)
    latency_ms = Column(Float, nullable=True)
    actual_price = Column(Float, nullable=True)

    __table_args__ = (
        Index('idx_timestamp_model', 'timestamp', 'model_version'),
    )

    def __repr__(self):
        return f"<Prediction(id={self.id}, price={self.predicted_price}, timestamp={self.timestamp})>"


def get_database_url():
    return os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/flightprice'
    )


def create_tables():
    engine = create_engine(get_database_url())
    Base.metadata.create_all(engine)
    print("Database tables created successfully")


def get_session():
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    return Session()


if __name__ == "__main__":
    create_tables()
