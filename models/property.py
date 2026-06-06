from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, func
from database import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, default="")
    price = Column(Float, nullable=False)
    rent = Column(Float, nullable=True, default=None)
    currency = Column(String, default="€")
    operation = Column(String, default="venta")
    property_type = Column(String, default="piso")
    bedrooms = Column(Integer, default=0)
    bathrooms = Column(Integer, default=0)
    surface = Column(Float, default=0)
    surface_unit = Column(String, default="m²")
    location = Column(String, default="")
    address = Column(String, default="")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    features = Column(Text, default="")
    images = Column(Text, default="")
    video_url = Column(String, default="")
    tour_url = Column(String, default="")
    status = Column(String, default="disponible")
    featured = Column(Boolean, default=False)
    views = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
