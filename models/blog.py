from sqlalchemy import Column, Integer, String, Text, DateTime, func
from database import Base


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    excerpt = Column(Text, default="")
    content = Column(Text, default="")
    image = Column(String, default="")
    author = Column(String, default="Otro Enfoque Inmobiliaria")
    published = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
