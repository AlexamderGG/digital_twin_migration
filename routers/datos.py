# routers/datos.py
from fastapi import APIRouter, Depends
from routers.auth import get_current_user_api
from modules.data_ingestion import DataManager

router = APIRouter()

@router.get("/especies")
def obtener_especies(current_user: dict = Depends(get_current_user_api)):
    # Protegido por el token JWT
    especies = DataManager.get_especies()
    return {"success": True, "data": especies}

@router.get("/resumen")
def obtener_resumen(current_user: dict = Depends(get_current_user_api)):
    resumen = DataManager.get_resumen_datos()
    return {"success": True, "data": resumen}