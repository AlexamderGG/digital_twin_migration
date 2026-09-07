"""
Módulo de Ingesta y Gestión de Datos
Gemelo Digital de Corredores de Migración

Integra datos de:
- GBIF: registros de presencia de especies
- WorldClim + CMIP6: variables climáticas
- Landsat/Sentinel: uso del suelo
- Telemetría: trayectorias de movimiento
- Ciencia ciudadana: observaciones complementarias
"""

import logging
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, MultiPolygon
from sqlalchemy import text

from config import Config, DatabaseConnection

logger = logging.getLogger(__name__)


class DataIngestion:
    """Gestor de ingesta y procesamiento de datos"""
    
    @staticmethod
    def cargar_registros_gbif(df: pd.DataFrame, id_especie: int, 
                              fuente: str = 'GBIF') -> Dict[str, Any]:
        """
        Carga registros de presencia desde un DataFrame estilo GBIF
        
        Columnas esperadas: decimalLatitude, decimalLongitude, eventDate,
                           occurrenceID, coordinateUncertaintyInMeters
        """
        try:
            # Limpieza y filtrado
            df_limpio = df.copy()
            
            # Renombrar columnas comunes
            column_map = {
                'decimalLatitude': 'latitud',
                'decimalLongitude': 'longitud',
                'eventDate': 'fecha_observacion',
                'occurrenceID': 'id_fuente_original',
                'coordinateUncertaintyInMeters': 'certeza'
            }
            df_limpio = df_limpio.rename(columns={k: v for k, v in column_map.items() 
                                                   if k in df_limpio.columns})
            
            # Filtrar coordenadas válidas
            df_limpio = df_limpio.dropna(subset=['latitud', 'longitud'])
            df_limpio = df_limpio[
                (df_limpio['latitud'].between(-90, 90)) &
                (df_limpio['longitud'].between(-180, 180))
            ]
            
            # Convertir certeza (incertidumbre a valor de confianza)
            if 'certeza' in df_limpio.columns:
                df_limpio['certeza'] = 1.0 / (1.0 + df_limpio['certeza'].fillna(1000) / 1000)
            else:
                df_limpio['certeza'] = 1.0
            
            # Procesar fechas
            if 'fecha_observacion' in df_limpio.columns:
                df_limpio['fecha_observacion'] = pd.to_datetime(
                    df_limpio['fecha_observacion'], errors='coerce'
                ).dt.date
            
            # Eliminar duplicados espaciales
            df_limpio = df_limpio.drop_duplicates(subset=['latitud', 'longitud'])
            
            if len(df_limpio) == 0:
                return {"success": False, "error": "No hay registros válidos después de la limpieza"}
            
            # Insertar en lote
            engine = DatabaseConnection.get_engine()
            registros_insertados = 0
            
            with engine.connect() as conn:
                for _, row in df_limpio.iterrows():
                    lat = float(row['latitud'])
                    lon = float(row['longitud'])
                    fecha = row.get('fecha_observacion')
                    id_orig = str(row.get('id_fuente_original', ''))[:100]
                    certeza = float(row.get('certeza', 1.0))
                    
                    query = """
                        INSERT INTO registros_presencia 
                        (id_especie, fecha_observacion, ubicacion, latitud, longitud,
                         fuente, id_fuente_original, certeza)
                        VALUES (:id_especie, :fecha, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                                :lat, :lon, :fuente, :id_orig, :certeza)
                        ON CONFLICT DO NOTHING
                    """
                    result = conn.execute(text(query), {
                        "id_especie": id_especie,
                        "fecha": fecha,
                        "lon": lon,
                        "lat": lat,
                        "fuente": fuente,
                        "id_orig": id_orig,
                        "certeza": certeza
                    })
                    registros_insertados += result.rowcount
                
                conn.commit()
            
            logger.info(f"Registros cargados: {registros_insertados} para especie ID {id_especie}")
            return {
                "success": True,
                "registros_insertados": registros_insertados,
                "registros_filtrados": len(df) - len(df_limpio)
            }
            
        except Exception as e:
            logger.error(f"Error en carga GBIF: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def cargar_telemetria(df: pd.DataFrame, id_especie: int) -> Dict[str, Any]:
        """Carga datos de telemetría GPS"""
        try:
            df_limpio = df.copy()
            
            # Columnas esperadas
            required = ['latitud', 'longitud', 'fecha_hora']
            missing = [c for c in required if c not in df_limpio.columns]
            if missing:
                return {"success": False, "error": f"Columnas faltantes: {missing}"}
            
            df_limpio = df_limpio.dropna(subset=['latitud', 'longitud'])
            df_limpio['fecha_hora'] = pd.to_datetime(df_limpio['fecha_hora'], errors='coerce')
            df_limpio = df_limpio.dropna(subset=['fecha_hora'])
            
            engine = DatabaseConnection.get_engine()
            insertados = 0
            
            with engine.connect() as conn:
                for _, row in df_limpio.iterrows():
                    query = """
                        INSERT INTO telemetria 
                        (id_especie, id_individuo, fecha_hora, ubicacion, latitud, longitud,
                         altitud, velocidad, direccion, precision_gps, dispositivo, fuente)
                        VALUES (:id_especie, :id_ind, :fecha_hora, 
                                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                                :lat, :lon, :alt, :vel, :dir, :prec, :disp, :fuente)
                    """
                    result = conn.execute(text(query), {
                        "id_especie": id_especie,
                        "id_ind": str(row.get('id_individuo', 'desconocido'))[:50],
                        "fecha_hora": row['fecha_hora'],
                        "lon": float(row['longitud']),
                        "lat": float(row['latitud']),
                        "alt": float(row.get('altitud', 0)) if pd.notna(row.get('altitud')) else None,
                        "vel": float(row.get('velocidad', 0)) if pd.notna(row.get('velocidad')) else None,
                        "dir": float(row.get('direccion', 0)) if pd.notna(row.get('direccion')) else None,
                        "prec": float(row.get('precision_gps', 0)) if pd.notna(row.get('precision_gps')) else None,
                        "disp": str(row.get('dispositivo', ''))[:100],
                        "fuente": str(row.get('fuente', 'telemetria'))[:100]
                    })
                    insertados += result.rowcount
                conn.commit()
            
            return {"success": True, "registros_insertados": insertados}
            
        except Exception as e:
            logger.error(f"Error en carga telemetría: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def cargar_uso_suelo(gdf: gpd.GeoDataFrame, año: int, 
                         clase_col: str = 'clase_uso') -> Dict[str, Any]:
        """Carga capa de uso del suelo desde GeoDataFrame"""
        try:
            if gdf.crs is None:
                gdf = gdf.set_crs(Config.DEFAULT_CRS)
            elif gdf.crs != Config.DEFAULT_CRS:
                gdf = gdf.to_crs(Config.DEFAULT_CRS)
            
            engine = DatabaseConnection.get_engine()
            insertados = 0
            
            with engine.connect() as conn:
                for _, row in gdf.iterrows():
                    geom = row.geometry
                    if geom is None:
                        continue
                    
                    # Calcular área en km²
                    area_km2 = float(gpd.GeoSeries([geom], crs=gdf.crs).to_crs('EPSG:6933').area.iloc[0]) / 1e6
                    
                    query = """
                        INSERT INTO uso_suelo 
                        (año, fuente, geometria, clase_uso, codigo_clase, area_km2, porcentaje_vegetacion)
                        VALUES (:año, :fuente, ST_SetSRID(ST_GeomFromText(:geom_wkt), 4326),
                                :clase, :codigo, :area, :veg)
                    """
                    result = conn.execute(text(query), {
                        "año": año,
                        "fuente": str(row.get('fuente', 'Sentinel-2'))[:100],
                        "geom_wkt": geom.wkt,
                        "clase": str(row.get(clase_col, 'desconocido'))[:100],
                        "codigo": int(row.get('codigo_clase', 0)) if pd.notna(row.get('codigo_clase')) else 0,
                        "area": area_km2,
                        "veg": float(row.get('porcentaje_vegetacion', 0)) if pd.notna(row.get('porcentaje_vegetacion')) else 0
                    })
                    insertados += result.rowcount
                conn.commit()
            
            return {"success": True, "poligonos_insertados": insertados}
            
        except Exception as e:
            logger.error(f"Error en carga uso del suelo: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def descargar_gbif_especie(nombre_cientifico: str, limite: int = 5000) -> Optional[pd.DataFrame]:
        """Descarga registros de presencia desde GBIF API"""
        try:
            import requests
            
            url = "https://api.gbif.org/v1/occurrence/search"
            params = {
                "scientificName": nombre_cientifico,
                "hasCoordinate": True,
                "hasGeospatialIssue": False,
                "limit": min(limite, 300),
                "offset": 0
            }
            
            all_records = []
            
            while len(all_records) < limite:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                records = data.get('results', [])
                if not records:
                    break
                
                all_records.extend(records)
                
                if data.get('endOfRecords', True):
                    break
                
                params['offset'] += len(records)
            
            if not all_records:
                return None
            
            df = pd.DataFrame(all_records)
            logger.info(f"Descargados {len(df)} registros de GBIF para {nombre_cientifico}")
            return df
            
        except Exception as e:
            logger.error(f"Error descargando GBIF: {e}")
            return None


class DataManager:
    """Gestor de consulta y recuperación de datos"""
    
    @staticmethod
    def get_especies() -> List[Dict[str, Any]]:
        """Obtiene catálogo de especies"""
        query = """
            SELECT id_especie, nombre_cientifico, nombre_comun, clase, orden,
                   familia, categoria_uicn, habitat_pref
            FROM especies
            ORDER BY nombre_cientifico
        """
        return DatabaseConnection.execute_query(query)
    
    @staticmethod
    def get_registros_presencia(id_especie: int = None, 
                                limit: int = 10000) -> gpd.GeoDataFrame:
        """Obtiene registros de presencia como GeoDataFrame"""
        query = """
            SELECT id_registro, id_especie, fecha_observacion, latitud, longitud,
                   fuente, certeza, ubicacion as geometria
            FROM registros_presencia
            WHERE (:id_especie IS NULL OR id_especie = :id_especie)
            ORDER BY fecha_observacion DESC NULLS LAST
            LIMIT :limit
        """
        return DatabaseConnection.read_geodataframe(
            query, 
            params={"id_especie": id_especie, "limit": limit}
        )
    
    @staticmethod
    def get_telemetria(id_especie: int = None, 
                       id_individuo: str = None) -> gpd.GeoDataFrame:
        """Obtiene datos de telemetría"""
        query = """
            SELECT id_telemetria, id_especie, id_individuo, fecha_hora,
                   latitud, longitud, velocidad, altitud, ubicacion as geometria
            FROM telemetria
            WHERE (:id_especie IS NULL OR id_especie = :id_especie)
              AND (:id_individuo IS NULL OR id_individuo = :id_individuo)
            ORDER BY fecha_hora
        """
        return DatabaseConnection.read_geodataframe(
            query,
            params={"id_especie": id_especie, "id_individuo": id_individuo}
        )
    
    @staticmethod
    def get_uso_suelo(año: int = None) -> gpd.GeoDataFrame:
        """Obtiene capa de uso del suelo"""
        query = """
            SELECT id_uso_suelo, año, clase_uso, codigo_clase, area_km2,
                   porcentaje_vegetacion, geometria
            FROM uso_suelo
            WHERE (:año IS NULL OR año = :año)
        """
        return DatabaseConnection.read_geodataframe(
            query,
            params={"año": año}
        )
    
    @staticmethod
    def get_resumen_datos() -> Dict[str, Any]:
        """Obtiene resumen estadístico de los datos cargados"""
        queries = {
            "total_especies": "SELECT COUNT(*) as cnt FROM especies",
            "total_registros": "SELECT COUNT(*) as cnt FROM registros_presencia",
            "total_telemetria": "SELECT COUNT(*) as cnt FROM telemetria",
            "total_uso_suelo": "SELECT COUNT(*) as cnt FROM uso_suelo",
            "total_simulaciones": "SELECT COUNT(*) as cnt FROM simulaciones",
            "total_usuarios": "SELECT COUNT(*) as cnt FROM usuarios WHERE activo = TRUE"
        }
        
        resultados = {}
        for key, query in queries.items():
            res = DatabaseConnection.execute_query(query)
            resultados[key] = res[0]['cnt'] if res else 0
        
        # Registros por especie
        query_especies = """
            SELECT e.nombre_cientifico, COUNT(r.id_registro) as total
            FROM especies e
            LEFT JOIN registros_presencia r ON e.id_especie = r.id_especie
            GROUP BY e.id_especie, e.nombre_cientifico
            ORDER BY total DESC
            LIMIT 10
        """
        resultados['registros_por_especie'] = DatabaseConnection.execute_query(query_especies)
        
        return resultados
