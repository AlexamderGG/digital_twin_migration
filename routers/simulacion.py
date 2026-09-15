# routers/simulacion.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from routers.auth import get_current_user_api
from modules.scenario_simulator import ScenarioSimulator

router = APIRouter()

# 1. Alineamos el esquema con lo que envía React
class SimulacionRequest(BaseModel):
    id_especie: int
    codigo_ssp: str
    año_inicio: int  # React deberá enviar esto (ej. 2024)
    año_fin: int     # React deberá enviar esto (ej. 2050)

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
        
        # Aquí adentro de ejecutar_comparacion() es donde tu sistema debe hacer el 
        # SELECT a la base de datos, buscar el mejor AUC y cargar el archivo .pkl
        # Ejecutamos la simulación
        resultados = simulador.ejecutar_comparacion()
        
        # CHISMOSO: Imprime en la consola negra de Python qué diccionario se generó
        print("\n--- RESULTADOS DEL SIMULADOR ---")
        print(resultados)
        print("--------------------------------\n")
        
        if resultados.get('success'):
            # Rescatamos la URL de forma segura
            url_img = resultados.get('url_mapa_resultado') or resultados.get('url_mapa')
            
            return {
                "success": True,
                "data": {
                    "mejora_pc_promedio": float(resultados['mejora_pc_promedio']),
                    "hipotesis_soportada": bool(resultados['hipotesis_soportada']),
                    "especie": resultados.get('especie', 'Desconocida'),
                    "escenario": resultados.get('codigo_ssp'),
                    
                    # ESTA ES LA LÍNEA CLAVE: Debe estar dentro de 'data'
                    "url_mapa_resultado": url_img 
                }
            }
        else:
            raise HTTPException(status_code=400, detail="Error interno al ejecutar la simulación")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))