import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from database import Base, SessionLocal, engine
from models import User
from Rutas import (
    alertas, compras, dashboard, inventario, logs,
    productos, proveedores, reportes, usuarios, ventas,
)
from Rutas.auth import hash_password
from fastapi.middleware.cors import CORSMiddleware
origins = [
    "http://localhost:5173",  # React + Vite
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

def crear_admin_inicial():
    """Si no existe ningún administrador, crea uno con ADMIN_USERNAME / ADMIN_PASSWORD."""
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    if not (username and password):
        return

    db = SessionLocal()
    try:
        if db.query(User).filter_by(role="admin").first():
            return

        db.add(
            User(
                username=username,
                email=os.getenv("ADMIN_EMAIL", f"{username}@local.invalid"),
                password=hash_password(password),
                role="admin",
            )
        )
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    crear_admin_inicial()
    yield


app = FastAPI(
    title="API de tienda de belleza",
    description="Documentación de la API para la gestión de inventario.",
    version="1.1.0",
    lifespan=lifespan,
)

# CORS
origenes = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origenes,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
for modulo in (
    usuarios, productos, proveedores, ventas, compras,
    inventario, alertas, reportes, dashboard, logs,
):
    app.include_router(modulo.router)


@app.get("/")
def index():
    return {"message": "API FastAPI funcionando correctamente"}
