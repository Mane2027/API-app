from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from Rutas import productos, usuarios

app = FastAPI(
    title="API de tienda de belleza",
    description="Documentación de la API para la gestión de productos y usuarios.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(productos.router)
app.include_router(usuarios.router)

@app.get("/")
def index():
    return {"message": "API FastAPI funcionando correctamente"}
