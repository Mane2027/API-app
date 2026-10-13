from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from Rutas import (
    productos, usuarios, reportes, inventario,
    alertas, proveedores, ventas, compras,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API de tienda de belleza",
    description="Documentación de la API para la gestión de inventario.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # o léelo de una variable de entorno
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for modulo in (productos, usuarios, proveedores, ventas, compras,
               inventario, alertas, reportes):
    app.include_router(modulo.router)

@app.get("/")
def index():
    return {"message": "API FastAPI funcionando correctamente"}

