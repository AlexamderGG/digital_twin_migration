# routers/simulacion.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from routers.auth import get_current_user_api
from modules.scenario_simulator import ScenarioSimulator

router = APIRouter()

# 1. Definimos el esquema exacto de lo que React nos debe enviar
class SimulacionRequest(BaseModel):
    id_especie: int
    codigo_ssp: str
    año_inicio: int
    año_fin: int

@router.post("/ejecutar")
def ejecutar_simulacion(req: SimulacionRequest, current_user: dict = Depends(get_current_user_api)):
    try:
        # Instanciamos la clase que ya tienes en modules/
        simulador = ScenarioSimulator(
            id_especie=req.id_especie,
            codigo_ssp=req.codigo_ssp,
            año_inicio=req.año_inicio,
            año_fin=req.año_fin
        )
        
        # Ejecutamos sin el progress_callback de Streamlit
        resultados = simulador.ejecutar_comparacion()
        
        if resultados.get('success'):
            # Retornamos solo datos serializables (tipos primitivos de Python)
            return {
                "success": True,
                "data": {
                    "mejora_pc_promedio": resultados['mejora_pc_promedio'],
                    "hipotesis_soportada": resultados['hipotesis_soportada'],
                    "especie": resultados.get('especie', 'Desconocida'),
                    "escenario": resultados.get('codigo_ssp')
                }
            }
        else:
            raise HTTPException(status_code=400, detail="Error interno al ejecutar la simulación")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))