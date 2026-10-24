import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, SessionLocal, engine
from models import User
from Rutas import (
    alertas, compras, dashboard, inventario, logs,
    productos, proveedores, reportes, usuarios, ventas,
)
from Rutas.auth import hash_password
from Rutas.recuperar import router as recuperar_router
from Rutas import export

app.include_router(export.router)



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

# CORS (después de crear app)
origenes = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origenes,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
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
    app.include_router(recuperar_router)
from Rutas.recuperar import router as recuperar_router



@app.get("/")
def index():
    return {"message": "API FastAPI funcionando correctamente"}
