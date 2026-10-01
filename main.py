from fastapi import FastAPI
from app.database import Base, engine
from app.routes import productos_router  # tus rutas

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(productos_router)
