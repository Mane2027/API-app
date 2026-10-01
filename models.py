from sqlalchemy import Column, Integer, String, Float, Boolean, Date, Text, DateTime
from app.database import Base
from datetime import datetime
created_at = Column(DateTime, default=datetime.utcnow)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    sku = Column(String(50), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text)
    brand = Column(String(100), nullable=False)
    category = Column(String(30), nullable=False, default="otro")
    price = Column(Float, nullable=False)
    cost = Column(Float)
    stock = Column(Integer, default=0)
    min_stock = Column(Integer, default=5)
    expiration_date = Column(Date)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(200), nullable=False)
    role = Column(String(20), default="user")  # user / admin

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    details = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class ProductHistory(Base):
    __tablename__ = "product_history"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, nullable=False)
    field = Column(String(50), nullable=False)
    old_value = Column(String(200))
    new_value = Column(String(200))
    changed_by = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)

class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, nullable=False)
    movement_type = Column(String(20))  # entrada / salida
    quantity = Column(Integer, nullable=False)
    previous_stock = Column(Integer, nullable=False)
    new_stock = Column(Integer, nullable=False)
    performed_by = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow)
