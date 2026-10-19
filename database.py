import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# En Docker se define DATABASE_URL (ruta absoluta = 4 barras: sqlite:////app/data/database.db).
# Sin la variable, usa ./data/database.db
DATABASE_URL = os.getenv("DATABASE_URL", "postgres:///./data/database.db")

if  DATABASE_URL.startswith("postgres://"):
    ruta =DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)
Base = declarative_base()
