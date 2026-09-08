# backend/routers/conectividad.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from routers.auth import get_current_user_api
from modules.circuit_theory import LandscapeGraph, ResistanceLayer
from modules.scenario_simulator import ScenarioSimulator

router = APIRouter()

class ConectividadRequest(BaseModel):
    id_especie: int
    codigo_ssp: str = "SSP2-4.5"

@router.post("/analizar")
def analizar_conectividad(req: ConectividadRequest, current_user: dict = Depends(get_current_user_api)):
    try:
        # Replicamos la lógica del módulo original usando el simulador base[cite: 1]
        simulador = ScenarioSimulator(id_especie=req.id_especie, codigo_ssp=req.codigo_ssp)
        gdf_parches = simulador._generar_parches_sinteticos(n_parches=20)
        gdf_uso_suelo = simulador._generar_uso_suelo_base(bounds=(-80, -15, -65, 5), resolucion=2.0)
        
        gdf_resistencia = ResistanceLayer.generar_capa_resistencia(gdf_uso_suelo)
        
        grafo = LandscapeGraph()
        grafo.construir_desde_parches(gdf_parches, gdf_resistencia, distancia_max=200)
        
        resultado = grafo.calcular_metricas_conectividad()
        
        return {
            "success": True,
            "data": {
                "pc": float(resultado.pc),
                "iic": float(resultado.iic),
                "ec": float(resultado.ec),
                "corriente_total": float(resultado.corriente_total)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))