from datetime import datetime
from typing import Any
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy import Column, DateTime, Integer


@as_declarative()
class Base:
    """
    Base class for all SQLAlchemy models
    """

    id: Any
    __name__: str

    # Generate __tablename__ automatically based on class name
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    # Common columns for all models
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def dict(self) -> dict:
        """Convert model instance to dictionary"""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }

    def update(self, **kwargs):
        """Update model instance with given kwargs"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self):
        """String representation of model instance"""
        attrs = []
        for column in self.__table__.columns:
            attrs.append(f"{column.name}={getattr(self, column.name)}")
        return f"<{self.__class__.__name__}({', '.join(attrs)})>"
