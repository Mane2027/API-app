from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timedelta
from jose import jwt, JWTError
import os

# ---------------------------------------------------------------------------
# Configuración de la aplicación FastAPI
# ---------------------------------------------------------------------------
app = FastAPI()
    title="API de tienda de belleza",
    description="Documentación de la API para la gestión de productos.",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Configuración de la base de datos
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ---------------------------------------------------------------------------
# Modelos SQLAlchemy
# ---------------------------------------------------------------------------
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

# Crear tablas
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Esquemas Pydantic
# ---------------------------------------------------------------------------
class ProductSchema(BaseModel):
    sku: str
    name: str
    description: str | None = None
    brand: str
    category: str = "otro"
    price: float
    cost: float | None = None
    stock: int = 0
    min_stock: int = 5
    expiration_date: str | None = None
    is_active: bool = True

# ---------------------------------------------------------------------------
# Dependencia de DB
# ---------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return {"message": "API FastAPI funcionando correctamente"}

# ---------------------- Productos ----------------------

@app.get("/api/products")
def get_products(db=Depends(get_db)):
    products = db.query(Product).all()
    return products

@app.post("/api/products")
def create_product(data: ProductSchema, db=Depends(get_db)):
    if db.query(Product).filter_by(sku=data.sku).first():
        raise HTTPException(status_code=409, detail="SKU ya registrado")

    product = Product(**data.dict())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

@app.get("/api/products/{product_id}")
def get_product(product_id: int, db=Depends(get_db)):
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product

@app.put("/api/products/{product_id}")
def update_product(product_id: int, data: ProductSchema, db=Depends(get_db)):
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    for key, value in data.dict().items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product

@app.delete("/api/products/{product_id}")
def delete_product(product_id: int, db=Depends(get_db)):
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    db.delete(product)
    db.commit()
    return {"message": "Producto eliminado correctamente"}

