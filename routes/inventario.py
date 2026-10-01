from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.dependencies import get_db
from app.models import Product, InventoryMovement
from Rutas.auth import verificar_token, require_role
from Rutas.logs import registrar_log

router = APIRouter(prefix="/inventario", tags=["Inventario"])
