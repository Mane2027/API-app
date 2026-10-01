from sqlalchemy import Column, Integer, String
from app.database import Base

class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    marca = Column(String(50), nullable=False)
    sku = Column(String(50), unique=True, nullable=False)
