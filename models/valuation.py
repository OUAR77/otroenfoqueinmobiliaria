from sqlalchemy import Column, Integer, String, Text, Float, DateTime, func
from database import Base


class ValuationRequest(Base):
    __tablename__ = "valuation_requests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, default="")
    property_type = Column(String, default="")
    address = Column(String, default="")
    surface = Column(Float, default=0)
    notes = Column(Text, default="")
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
