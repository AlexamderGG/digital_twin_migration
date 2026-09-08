# routers/habitat.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from routers.auth import get_current_user_api
from modules.habitat_suitability import HabitatSuitabilityModeler
import json
from config import DatabaseConnection

router = APIRouter()

class EntrenamientoRequest(BaseModel):
    id_especie: int
    algoritmo: str = "random_forest"
    test_size: float = 0.3

@router.post("/entrenar")
def entrenar_modelo(req: EntrenamientoRequest, current_user: dict = Depends(get_current_user_api)):
    try:
        modelador = HabitatSuitabilityModeler(req.id_especie, req.algoritmo)
        resultado = modelador.entrenar(test_size=req.test_size)
        
        if resultado:
            return {
                "success": True,
                "data": {
                    "auc": resultado.auc,
                    "tss": resultado.tss,
                    "accuracy": resultado.accuracy,
                    "variables_importance": {k: float(v) for k, v in resultado.variables_importance.items()}
                }
            }
        raise HTTPException(status_code=400, detail="No se pudo entrenar el modelo.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/modelo/{id_especie}")
def obtener_mejor_modelo(id_especie: int, current_user: dict = Depends(get_current_user_api)):
    try:
        query = """
            SELECT algoritmo, fecha_entrenamiento, auc, tss, accuracy, variables_importance
            FROM modelos_habitat
            WHERE id_especie = :id_especie
            ORDER BY auc DESC
            LIMIT 1
        """
        resultados = DatabaseConnection.execute_query(query, {"id_especie": id_especie})
        
        if resultados:
            modelo = resultados[0]
            
            # Convertimos el string JSON de la base de datos a diccionario si es necesario
            importancias = modelo['variables_importance']
            if isinstance(importancias, str):
                importancias = json.loads(importancias)
            
            # Formateamos para el frontend
            var_importantes = [
                {"nombre": k, "peso": float(v)} 
                for k, v in importancias.items()
            ]
            var_importantes.sort(key=lambda x: x["peso"], reverse=True)

            return {
                "success": True,
                "data": {
                    "algoritmo": modelo["algoritmo"],
                    "fecha_entrenamiento": str(modelo["fecha_entrenamiento"]),
                    "auc": float(modelo["auc"]),
                    "tss": float(modelo["tss"]),
                    "accuracy": float(modelo["accuracy"]),
                    "variables_importantes": var_importantes
                }
            }
        else:
            raise HTTPException(status_code=404, detail="No se encontró un modelo entrenado para esta especie.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))