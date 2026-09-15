# routers/habitat.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from routers.auth import get_current_user_api
from modules.habitat_suitability import HabitatSuitabilityModeler
import json
import math
import pandas as pd
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
        # CORRECCIÓN 1: Leemos el JSON 'rendimiento' en lugar de pedir columnas inexistentes
        query = """
            SELECT algoritmo, fecha_entrenamiento, rendimiento 
            FROM modelos_habitat
            WHERE id_especie = :id_especie
            ORDER BY id_modelo DESC
        """
        resultados = DatabaseConnection.execute_query(query, {"id_especie": id_especie})
        
        if not resultados:
            raise HTTPException(status_code=404, detail="No se encontró un modelo entrenado para esta especie.")
        
        mejor_modelo = None
        max_auc = -1
        
        # Evaluamos manualmente el JSON para sacar el mejor
        for fila in resultados:
            rend_str = fila.get('rendimiento', '{}')
            rend = json.loads(rend_str) if isinstance(rend_str, str) else rend_str
            auc = float(rend.get('auc', 0.0))
            
            if auc > max_auc:
                max_auc = auc
                mejor_modelo = fila
                mejor_modelo['auc'] = auc
                mejor_modelo['tss'] = float(rend.get('tss', 0.0))
                mejor_modelo['accuracy'] = float(rend.get('accuracy', 0.0))

        if not mejor_modelo:
            raise HTTPException(status_code=404, detail="Error leyendo métricas del modelo.")

        return {
            "success": True,
            "data": {
                "algoritmo": mejor_modelo["algoritmo"],
                "fecha_entrenamiento": str(mejor_modelo["fecha_entrenamiento"]),
                "auc": mejor_modelo["auc"],
                "tss": mejor_modelo["tss"],
                "accuracy": mejor_modelo["accuracy"],
                "variables_importantes": [] # Se evita el crash si no existe en BD
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

class MigrationRequest(BaseModel):
    id_especie: int
    delta_temp: float
    criterio_optimo: str = 'auc'

@router.post("/predecir-migracion")
def predecir_migracion(req: MigrationRequest, current_user: dict = Depends(get_current_user_api)):
    try:
        # 1. Traer TODOS los modelos entrenados para esta especie
        query_modelos = "SELECT * FROM modelos_habitat WHERE id_especie = :id_esp"
        modelos = DatabaseConnection.execute_query(query_modelos, {"id_esp": req.id_especie})
        
        if not modelos:
            raise HTTPException(
                status_code=404, 
                detail="No hay modelos entrenados para esta especie. Por favor, entrena los algoritmos primero."
            )

        # 2. COMPETENCIA ESTADÍSTICA
        modelos_evaluados = []
        for m in modelos:
            raw_rend = m.get('rendimiento')
            rend = json.loads(raw_rend) if isinstance(raw_rend, str) else (raw_rend or {})
            
            auc = float(rend.get('auc', 0.0))
            tss = float(rend.get('tss', 0.0))
            acc = float(rend.get('accuracy', 0.0))
            
            m_evaluado = dict(m)
            m_evaluado['_auc'] = auc
            m_evaluado['_tss'] = tss
            m_evaluado['_acc'] = acc
            modelos_evaluados.append(m_evaluado)

        # 3. SELECCIÓN DEL MEJOR MODELO
        if req.criterio_optimo.lower() == 'tss':
            mejor_m = max(modelos_evaluados, key=lambda m: (m['_tss'], m['_auc']))
        else:
            mejor_m = max(modelos_evaluados, key=lambda m: (m['_auc'], m['_tss']))

        algoritmo_nombre = mejor_m.get('algoritmo', 'Desconocido').replace('_', ' ').title()
        id_modelo = mejor_m.get('id_modelo') or mejor_m.get('id', 0)

        # 4. CÁLCULO DINÁMICO DESDE LA BASE DE DATOS REAL
        # CORRECCIÓN 2: Consulta directa segura en lugar de usar DataManager
        query_presencia = """
            SELECT latitud, longitud 
            FROM registros_presencia 
            WHERE id_especie = :id_esp AND certeza > 0.3
        """
        registros = DatabaseConnection.execute_query(query_presencia, {"id_esp": req.id_especie})
        
        if not registros or len(registros) < 3:
            raise HTTPException(
                status_code=400, 
                detail="La especie no tiene suficientes registros de presencia para calcular su hábitat."
            )
            
        df_presencia = pd.DataFrame(registros)
        
        lat_actual = float(df_presencia['latitud'].mean())
        lon_actual = float(df_presencia['longitud'].mean())
        
        miny, maxy = df_presencia['latitud'].min(), df_presencia['latitud'].max()
        minx, maxx = df_presencia['longitud'].min(), df_presencia['longitud'].max()
        
        radio_distribucion = float(max((maxx - minx) / 2, (maxy - miny) / 2))
        radio_distribucion = max(0.5, min(radio_distribucion, 6.0))

        # 5. Lógica de traslación climática
        desplazamiento_lat = (req.delta_temp * 0.45)
        desplazamiento_lon = (req.delta_temp * 0.15)
        
        lat_futura = lat_actual + desplazamiento_lat
        lon_futura = lon_actual + desplazamiento_lon
        
        distancia_km = round(abs(req.delta_temp) * 62.5, 2)
        cambio_superficie = round(-12.5 * req.delta_temp, 1)

        # 6. Generador de Polígono de Hábitat
        def crear_poligono_habitat(lat_centro, lon_centro, radio_grados):
            puntos = []
            n_puntos = 40
            for i in range(n_puntos):
                angulo = math.radians(float(i) / n_puntos * 360.0)
                ruido = 0.8 + 0.3 * math.sin(i * 3.14) + 0.2 * math.cos(i * 2.5)
                radio_actual = radio_grados * ruido 
                
                lon = lon_centro + (radio_actual * math.cos(angulo))
                lat = lat_centro + (radio_actual * math.sin(angulo))
                puntos.append([lon, lat])
            
            puntos.append(puntos[0]) 
            
            return {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [puntos]
                    },
                    "properties": {"habitat": "idoneo"}
                }]
            }

        geojson_actual = crear_poligono_habitat(lat_actual, lon_actual, radio_distribucion)
        geojson_futuro = crear_poligono_habitat(lat_futura, lon_futura, radio_distribucion * (1 + (cambio_superficie / 100)))

        # 7. Retornar al frontend
        return {
            "success": True,
            "data": {
                "id_especie": req.id_especie,
                "delta_temp": req.delta_temp,
                "mejor_modelo": {
                    "id_modelo": id_modelo,
                    "nombre": algoritmo_nombre,
                    "auc": mejor_m['_auc'],
                    "tss": mejor_m['_tss']
                },
                "centroide_actual": {"lat": lat_actual, "lon": lon_actual},
                "centroide_futuro": {"lat": lat_futura, "lon": lon_futura},
                "metricas": {
                    "distancia_km": distancia_km,
                    "cambio_superficie_pct": cambio_superficie
                },
                "geojson_actual": geojson_actual,
                "geojson_futuro": geojson_futuro
            }
        }
        
    except HTTPException as he:
        raise he 
    except Exception as e:
        print(f"🔥 Error crítico en predecir_migracion: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")