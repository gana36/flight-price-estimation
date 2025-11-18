"""
Database models for storing predictions and monitoring.
Uses SQLAlchemy ORM with PostgreSQL.
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, JSON, Index, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()


class Prediction(Base):
    """Model for storing flight price predictions."""

    __tablename__ = 'predictions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Input features (stored as JSON for flexibility)
    features = Column(JSON, nullable=False)

    # Prediction outputs
    predicted_price = Column(Float, nullable=False)

    # Model metadata
    model_name = Column(String(100), nullable=True, index=True)
    model_version = Column(String(50), nullable=True, index=True)

    # Performance tracking
    latency_ms = Column(Float, nullable=True)

    # Optional: actual price (for feedback loop)
    actual_price = Column(Float, nullable=True)

    # Create composite index for common queries
    __table_args__ = (
        Index('idx_timestamp_model', 'timestamp', 'model_version'),
    )

    def __repr__(self):
        return f"<Prediction(id={self.id}, price={self.predicted_price}, timestamp={self.timestamp})>"


def get_database_url():
    """Get database URL from environment or use default."""
    return os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/flightprice'
    )


def create_tables():
    """Create all database tables."""
    engine = create_engine(get_database_url())
    Base.metadata.create_all(engine)
    print("Database tables created successfully")


def get_session():
    """Get database session."""
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    return Session()


if __name__ == "__main__":
    create_tables()
