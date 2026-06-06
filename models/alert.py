from sqlalchemy import Column, Integer, String, Text, DateTime, func
from database import Base


class SearchAlert(Base):
    __tablename__ = "search_alerts"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)
    name = Column(String, default="")
    operation = Column(String, default="")
    property_type = Column(String, default="")
    min_price = Column(String, default="")
    max_price = Column(String, default="")
    location = Column(String, default="")
    active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
