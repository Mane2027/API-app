import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    if os.getenv("RENDER"):  # Render define esta variable automáticamente
        raise RuntimeError("Falta DATABASE_URL en producción")
    # Solo desarrollo local
    os.makedirs("data", exist_ok=True)
    DATABASE_URL = "sqlite:///./data/database.db"

# Algunos proveedores entregan "postgres://", SQLAlchemy exige "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # comprueba que la conexión siga viva antes de usarla
        pool_recycle=300,    # renueva conexiones cada 5 minutos
    )

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, expire_on_commit=False, bind=engine
)
Base = declarative_base()
