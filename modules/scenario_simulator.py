"""
Módulo de Simulación de Escenarios y Optimización Dinámica
Gemelo Digital de Corredores de Migración

Implementa:
- Simulación de escenarios climáticos SSP1-2.6, SSP2-4.5, SSP5-8.5
- Proyecciones de cambio de uso del suelo hasta 2050
- Comparación entre red estática y red dinámica
- Optimización de redes de corredores
- Cálculo de métricas de robustez
"""

import logging
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon, LineString, MultiPoint, box
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist

from config import Config, DatabaseConnection
from modules.habitat_suitability import HabitatSuitabilityModeler
from modules.circuit_theory import LandscapeGraph, ResistanceLayer
from modules.deep_learning import SpatiotemporalPredictor

logger = logging.getLogger(__name__)


@dataclass
class EscenarioResultado:
    """Resultados de un escenario simulado"""
    id_simulacion: Optional[int]
    nombre: str
    tipo: str
    codigo_ssp: str
    años: List[int]
    metricas_conectividad: pd.DataFrame  # columnas: año, pc, iic, ec, corriente
    corredores: gpd.GeoDataFrame
    parches: gpd.GeoDataFrame
    mejora_vs_estatico: Optional[float] = None


class ClimateScenario:
    """Generador de escenarios climáticos SSP"""
    
    # Factores de cambio por escenario SSP (delta por década)
    FACTORES_SSP = {
        'SSP1-2.6': {'delta_temp': 0.15, 'delta_precip': 0.02, 'delta_extremos': 0.1},
        'SSP2-4.5': {'delta_temp': 0.28, 'delta_precip': -0.03, 'delta_extremos': 0.25},
        'SSP5-8.5': {'delta_temp': 0.55, 'delta_precip': -0.08, 'delta_extremos': 0.5}
    }
    
    @classmethod
    def aplicar_escenario(cls, variables_base: pd.DataFrame,
                         codigo_ssp: str, año_objetivo: int,
                         año_base: int = 2020) -> pd.DataFrame:
        """
        Aplica un escenario climático a variables base
        """
        factores = cls.FACTORES_SSP.get(codigo_ssp, cls.FACTORES_SSP['SSP2-4.5'])
        décadas = (año_objetivo - año_base) / 10.0
        
        variables = variables_base.copy()
        
        # Aplicar cambios a variables de temperatura
        columnas_temp = [c for c in variables.columns if 'temp' in c.lower()]
        for col in columnas_temp:
            variables[col] += factores['delta_temp'] * décadas
        
        # Aplicar cambios a precipitación
        columnas_precip = [c for c in variables.columns if 'precip' in c.lower()]
        for col in columnas_precip:
            variables[col] *= (1 + factores['delta_precip'] * décadas)
            variables[col] = np.clip(variables[col], 0, None)
        
        # Aumentar variabilidad/estacionalidad
        if 'bio4_temp_estacionalidad' in variables.columns:
            variables['bio4_temp_estacionalidad'] *= (1 + factores['delta_extremos'] * décadas * 0.1)
        
        return variables


class LandUseSimulator:
    """Simulador de cambio de uso del suelo"""
    
    # Probabilidades de transición entre tipos de uso
    MATRIZ_TRANSICION = {
        'SSP1-2.6': {
            'bosque_humedo': {'bosque_humedo': 0.95, 'matorral': 0.03, 'agricultura': 0.02},
            'matorral': {'bosque_humedo': 0.05, 'matorral': 0.85, 'pastizal': 0.05, 'agricultura': 0.05},
            'agricultura': {'bosque_humedo': 0.02, 'agricultura': 0.88, 'urbano': 0.10},
            'pastizal': {'matorral': 0.05, 'pastizal': 0.85, 'agricultura': 0.10},
            'urbano': {'urbano': 0.98, 'agricultura': 0.02}
        },
        'SSP2-4.5': {
            'bosque_humedo': {'bosque_humedo': 0.88, 'matorral': 0.05, 'agricultura': 0.07},
            'matorral': {'bosque_humedo': 0.02, 'matorral': 0.75, 'pastizal': 0.08, 'agricultura': 0.15},
            'agricultura': {'agricultura': 0.82, 'urbano': 0.15, 'matorral': 0.03},
            'pastizal': {'matorral': 0.03, 'pastizal': 0.75, 'agricultura': 0.20, 'urbano': 0.02},
            'urbano': {'urbano': 0.99, 'agricultura': 0.01}
        },
        'SSP5-8.5': {
            'bosque_humedo': {'bosque_humedo': 0.75, 'matorral': 0.08, 'agricultura': 0.15, 'pastizal': 0.02},
            'matorral': {'matorral': 0.60, 'pastizal': 0.10, 'agricultura': 0.25, 'desierto': 0.05},
            'agricultura': {'agricultura': 0.70, 'urbano': 0.25, 'desierto': 0.05},
            'pastizal': {'pastizal': 0.60, 'agricultura': 0.25, 'desierto': 0.15},
            'urbano': {'urbano': 1.0}
        }
    }
    
    @classmethod
    def simular_cambio(cls, gdf_uso_suelo: gpd.GeoDataFrame,
                      codigo_ssp: str, años_proyeccion: int = 30) -> gpd.GeoDataFrame:
        """
        Simula cambio de uso del suelo basado en matriz de transición
        """
        matriz = cls.MATRIZ_TRANSICION.get(codigo_ssp, cls.MATRIZ_TRANSICION['SSP2-4.5'])
        gdf = gdf_uso_suelo.copy()
        
        n_pasos = años_proyeccion // 5  # Pasos de 5 años
        
        for paso in range(n_pasos):
            nuevas_clases = []
            
            for _, row in gdf.iterrows():
                clase_actual = str(row.get('clase_uso', 'matorral')).lower().replace(' ', '_')
                
                if clase_actual in matriz:
                    transiciones = matriz[clase_actual]
                    clases = list(transiciones.keys())
                    probs = list(transiciones.values())
                    
                    # Elevar probabilidades al número de pasos
                    probs = np.array(probs) ** (1.0 / n_pasos)
                    probs = probs / probs.sum()
                    
                    nueva_clase = np.random.choice(clases, p=probs)
                else:
                    nueva_clase = clase_actual
                
                nuevas_clases.append(nueva_clase.replace('_', ' ').title())
            
            gdf['clase_uso'] = nuevas_clases
        
        return gdf


class ScenarioSimulator:
    """Simulador principal de escenarios"""
    
    def __init__(self, id_especie: int, codigo_ssp: str = 'SSP2-4.5',
                 año_inicio: int = 2024, año_fin: int = 2050):
        self.id_especie = id_especie
        self.codigo_ssp = codigo_ssp
        self.año_inicio = año_inicio
        self.año_fin = año_fin
        self.años = list(range(año_inicio, año_fin + 1))
        
        # Datos de la especie
        especie_data = DatabaseConnection.execute_query(
            "SELECT * FROM especies WHERE id_especie = :id",
            {"id": id_especie}
        )
        self.especie = especie_data[0] if especie_data else None
    
    def _generar_parches_sinteticos(self, n_parches: int = 15,
                                    bounds: Tuple = (-80, -15, -65, 5)) -> gpd.GeoDataFrame:
        """Genera parches de hábitat sintéticos para simulación"""
        np.random.seed(hash(str(self.id_especie) + self.codigo_ssp) % 2**32)
        
        minx, miny, maxx, maxy = bounds
        parches = []
        
        for i in range(n_parches):
            cx = np.random.uniform(minx + 2, maxx - 2)
            cy = np.random.uniform(miny + 2, maxy - 2)
            radio = np.random.uniform(0.3, 1.5)
            
            # Crear polígono circular irregular
            angulos = np.linspace(0, 2 * np.pi, 20)
            radios = radio * (1 + 0.2 * np.sin(angulos * 3 + np.random.rand()))
            puntos = [(cx + r * np.cos(a), cy + r * np.sin(a)) for a, r in zip(angulos, radios)]
            geom = Polygon(puntos)
            
            calidad = np.random.uniform(0.3, 0.95)
            
            parches.append({
                'id_parche': i,
                'geometry': geom,
                'calidad_habitat': calidad,
                'area_km2': float(gpd.GeoSeries([geom], crs='EPSG:4326').to_crs('EPSG:6933').area.iloc[0]) / 1e6
            })
        
        # Forma robusta: extraer geometrías separadamente
        geometrias = [p.pop('geometry') for p in parches]
        return gpd.GeoDataFrame(parches, geometry=geometrias, crs=Config.DEFAULT_CRS)
    
    def _generar_uso_suelo_base(self, bounds: Tuple, 
                               resolucion: float = 1.0) -> gpd.GeoDataFrame:
        """Genera capa base de uso del suelo"""
        minx, miny, maxx, maxy = bounds
        
        # Crear grilla de polígonos
        lons = np.arange(minx, maxx, resolucion)
        lats = np.arange(miny, maxy, resolucion)
        
        poligonos = []
        for i in range(len(lons) - 1):
            for j in range(len(lats) - 1):
                poly = box(lons[i], lats[j], lons[i+1], lats[j+1])
                poligonos.append(poly)
        
        # Forma robusta: pasar geometrías directamente al parámetro geometry=
        gdf = gpd.GeoDataFrame(geometry=poligonos, crs=Config.DEFAULT_CRS)
        
        # Asignar clases de uso del suelo
        np.random.seed(42)
        clases = ['bosque humedo', 'matorral', 'pastizal', 'agricultura', 'urbano']
        probs = [0.35, 0.25, 0.20, 0.15, 0.05]
        
        gdf['clase_uso'] = np.random.choice(clases, size=len(gdf), p=probs)
        gdf['año'] = self.año_inicio
        
        return gdf
    
    def simular_estatico(self, progress_callback=None) -> EscenarioResultado:
        """
        Simula red de corredores DISEÑO ESTÁTICO:
        Se diseña una sola vez con datos actuales y se mantiene constante
        """
        logger.info(f"Simulando escenario ESTÁTICO - {self.codigo_ssp}")
        
        # Generar datos base
        bounds = (-80, -15, -65, 5)
        gdf_parches = self._generar_parches_sinteticos(bounds=bounds)
        gdf_uso_suelo = self._generar_uso_suelo_base(bounds)
        
        # Diseñar red UNA SOLA VEZ al inicio
        gdf_resistencia = ResistanceLayer.generar_capa_resistencia(gdf_uso_suelo)
        
        grafo = LandscapeGraph(self.id_especie)
        grafo.construir_desde_parches(gdf_parches, gdf_resistencia, distancia_max=150)
        
        # Red estática diseñada al inicio
        corredores_estaticos = grafo.identificar_corredores(umbral_corriente=0.15)
        corredores_estaticos['tipo'] = 'estatico'
        corredores_estaticos['año_diseno'] = self.año_inicio
        
        # Evaluar a lo largo del tiempo (la red NO cambia, pero el paisaje sí)
        metricas_anuales = []
        uso_suelo_actual = gdf_uso_suelo.copy()
        
        for idx, año in enumerate(self.años):
            if progress_callback:
                progress_callback(idx / len(self.años), f"Estático - Año {año}")
            
            # Simular cambio en uso del suelo
            delta_años = año - self.año_inicio
            if delta_años > 0:
                uso_suelo_actual = LandUseSimulator.simular_cambio(
                    gdf_uso_suelo, self.codigo_ssp, años_proyeccion=delta_años
                )
            
            # Actualizar resistencia (el paisaje cambia, pero los corredores NO)
            gdf_resistencia_actual = ResistanceLayer.generar_capa_resistencia(uso_suelo_actual)
            
            # Evaluar conectividad de la red ESTÁTICA en el paisaje actual
            grafo_eval = LandscapeGraph(self.id_especie)
            grafo_eval.construir_desde_parches(gdf_parches, gdf_resistencia_actual, distancia_max=150)
            
            resultado = grafo_eval.calcular_metricas_conectividad()
            
            metricas_anuales.append({
                'año': año,
                'pc': resultado.pc,
                'iic': resultado.iic,
                'ec': resultado.ec,
                'corriente_total': resultado.corriente_total
            })
        
        df_metricas = pd.DataFrame(metricas_anuales)
        
        return EscenarioResultado(
            id_simulacion=None,
            nombre=f"Estático - {self.codigo_ssp}",
            tipo='estatico',
            codigo_ssp=self.codigo_ssp,
            años=self.años,
            metricas_conectividad=df_metricas,
            corredores=corredores_estaticos,
            parches=gdf_parches
        )
    
    def simular_dinamico(self, progress_callback=None) -> EscenarioResultado:
        """
        Simula red de corredores DISEÑO DINÁMICO:
        La red se actualiza anualmente según el estado del paisaje
        """
        logger.info(f"Simulando escenario DINÁMICO - {self.codigo_ssp}")
        
        bounds = (-80, -15, -65, 5)
        gdf_parches = self._generar_parches_sinteticos(bounds=bounds)
        gdf_uso_suelo_base = self._generar_uso_suelo_base(bounds)
        
        metricas_anuales = []
        todos_corredores = []
        
        uso_suelo_actual = gdf_uso_suelo_base.copy()
        
        for idx, año in enumerate(self.años):
            if progress_callback:
                progress_callback(idx / len(self.años), f"Dinámico - Año {año}")
            
            # Simular cambio en uso del suelo
            delta_años = año - self.año_inicio
            if delta_años > 0:
                uso_suelo_actual = LandUseSimulator.simular_cambio(
                    gdf_uso_suelo_base, self.codigo_ssp, años_proyeccion=delta_años
                )
            
            # Aplicar escenario climático y ajustar parches
            gdf_parches_ajustados = gdf_parches.copy()
            factor_climatico = ClimateScenario.FACTORES_SSP.get(self.codigo_ssp, {})
            delta_temp = factor_climatico.get('delta_temp', 0.28) * delta_años / 10.0
            
            # Ajustar calidad de hábitat por clima
            gdf_parches_ajustados['calidad_habitat'] = gdf_parches_ajustados['calidad_habitat'] * \
                np.exp(-0.05 * abs(delta_temp - 1.5))  # Óptimo alrededor de +1.5°C
            
            # REDISEÑAR la red cada año
            gdf_resistencia = ResistanceLayer.generar_capa_resistencia(uso_suelo_actual)
            
            grafo = LandscapeGraph(self.id_especie)
            grafo.construir_desde_parches(gdf_parches_ajustados, gdf_resistencia, distancia_max=150)
            
            resultado = grafo.calcular_metricas_conectividad()
            
            metricas_anuales.append({
                'año': año,
                'pc': resultado.pc,
                'iic': resultado.iic,
                'ec': resultado.ec,
                'corriente_total': resultado.corriente_total
            })
            
            # Corredores de este año
            corredores_año = grafo.identificar_corredores(umbral_corriente=0.15)
            if len(corredores_año) > 0:
                corredores_año['año'] = año
                corredores_año['tipo'] = 'dinamico'
                todos_corredores.append(corredores_año)
        
        df_metricas = pd.DataFrame(metricas_anuales)
        
        if todos_corredores:
            gdf_corredores = pd.concat(todos_corredores, ignore_index=True)
            # Asegurar que es un GeoDataFrame con geometría válida
            if not isinstance(gdf_corredores, gpd.GeoDataFrame):
                gdf_corredores = gpd.GeoDataFrame(gdf_corredores, geometry='geometry', crs=Config.DEFAULT_CRS)
            elif gdf_corredores.crs is None:
                gdf_corredores = gdf_corredores.set_crs(Config.DEFAULT_CRS)
        else:
            # GeoDataFrame vacío (forma robusta)
            gdf_corredores = gpd.GeoDataFrame(
                {'año': [], 'tipo': []},
                geometry=[],
                crs=Config.DEFAULT_CRS
            )
        
        return EscenarioResultado(
            id_simulacion=None,
            nombre=f"Dinámico - {self.codigo_ssp}",
            tipo='dinamico',
            codigo_ssp=self.codigo_ssp,
            años=self.años,
            metricas_conectividad=df_metricas,
            corredores=gdf_corredores,
            parches=gdf_parches
        )
    
    def ejecutar_comparacion(self, progress_callback=None) -> Dict[str, Any]:
        """
        Ejecuta simulaciones estática y dinámica, y compara resultados
        """
        logger.info("Iniciando comparación Estático vs Dinámico")
        
        # Simular estático
        if progress_callback:
            progress_callback(0.0, "Iniciando simulación ESTÁTICA...")
        
        resultado_estatico = self.simular_estatico(
            progress_callback=lambda p, m: progress_callback(p * 0.4, m) if progress_callback else None
        )
        
        # Simular dinámico
        if progress_callback:
            progress_callback(0.4, "Iniciando simulación DINÁMICA...")
        
        resultado_dinamico = self.simular_dinamico(
            progress_callback=lambda p, m: progress_callback(0.4 + p * 0.5, m) if progress_callback else None
        )
        
        # Calcular mejora
        pc_estatico_final = resultado_estatico.metricas_conectividad['pc'].iloc[-1]
        pc_dinamico_final = resultado_dinamico.metricas_conectividad['pc'].iloc[-1]
        
        if pc_estatico_final > 0:
            mejora_pc = ((pc_dinamico_final - pc_estatico_final) / pc_estatico_final) * 100
        else:
            mejora_pc = 0.0
        
        # Mejora promedio a lo largo de todo el periodo
        pc_estatico_mean = resultado_estatico.metricas_conectividad['pc'].mean()
        pc_dinamico_mean = resultado_dinamico.metricas_conectividad['pc'].mean()
        
        if pc_estatico_mean > 0:
            mejora_pc_promedio = ((pc_dinamico_mean - pc_estatico_mean) / pc_estatico_mean) * 100
        else:
            mejora_pc_promedio = 0.0
        
        if progress_callback:
            progress_callback(0.95, "Guardando resultados...")
        
        # Guardar en base de datos
        simulacion_id = self._guardar_simulacion(
            resultado_estatico, resultado_dinamico, mejora_pc_promedio
        )
        
        resultado_estatico.id_simulacion = simulacion_id
        resultado_dinamico.id_simulacion = simulacion_id
        resultado_dinamico.mejora_vs_estatico = mejora_pc_promedio
        
        if progress_callback:
            progress_callback(1.0, "¡Comparación completada!")
        
        return {
            "success": True,
            "id_simulacion": simulacion_id,
            "mejora_pc_final": float(mejora_pc),
            "mejora_pc_promedio": float(mejora_pc_promedio),
            "hipotesis_soportada": mejora_pc_promedio >= 25.0,
            "resultado_estatico": resultado_estatico,
            "resultado_dinamico": resultado_dinamico,
            "codigo_ssp": self.codigo_ssp,
            "especie": self.especie['nombre_cientifico'] if self.especie else "Desconocida"
        }
    
    def _guardar_simulacion(self, res_estatico: EscenarioResultado,
                           res_dinamico: EscenarioResultado,
                           mejora: float) -> Optional[int]:
        """Guarda resultados de simulación en base de datos"""
        try:
            # Obtener ID de escenario
            escenario = DatabaseConnection.execute_query(
                "SELECT id_escenario FROM escenarios_climaticos WHERE codigo_ssp = :cod",
                {"cod": self.codigo_ssp}
            )
            id_escenario = escenario[0]['id_escenario'] if escenario else 2
            
            # Insertar simulación principal
            query = """
                INSERT INTO simulaciones
                (nombre, descripcion, tipo, id_escenario, id_especie,
                 año_inicio, año_fin, parametros, estado, progreso,
                 fecha_inicio, fecha_fin)
                VALUES (:nombre, :descripcion, :tipo, :id_escenario, :id_especie,
                        :año_inicio, :año_fin, :parametros, :estado, :progreso,
                        :fecha_inicio, :fecha_fin)
                RETURNING id_simulacion
            """
            
            results = DatabaseConnection.execute_query(query, {
                "nombre": f"Comparación {self.codigo_ssp} - {self.especie['nombre_cientifico'] if self.especie else 'sp.'}",
                "descripcion": f"Comparación diseño estático vs dinámico. Mejora PC promedio: {mejora:.2f}%",
                "tipo": "comparacion",
                "id_escenario": id_escenario,
                "id_especie": self.id_especie,
                "año_inicio": self.año_inicio,
                "año_fin": self.año_fin,
                "parametros": json.dumps({
                    "codigo_ssp": self.codigo_ssp,
                    "mejora_pc_promedio": float(mejora),
                    "hipotesis_soportada": bool(mejora >= 25.0)
                }),
                "estado": "completada",
                "progreso": 100,
                "fecha_inicio": datetime.now(),
                "fecha_fin": datetime.now()
            })
            
            if not results:
                return None
            
            id_simulacion = results[0]['id_simulacion']
            
            # Guardar métricas anuales
            for _, row in res_estatico.metricas_conectividad.iterrows():
                for metrica in ['pc', 'iic', 'ec', 'corriente_total']:
                    DatabaseConnection.execute_non_query("""
                        INSERT INTO resultados_conectividad
                        (id_simulacion, año, metrica, valor, unidad, descripcion)
                        VALUES (:id_sim, :año, :metrica, :valor, :unidad, :descripcion)
                    """, {
                        "id_sim": id_simulacion,
                        "año": int(row['año']),
                        "metrica": f"estatico_{metrica}",
                        "valor": float(row[metrica]),
                        "unidad": "adimensional" if metrica != 'corriente_total' else "A",
                        "descripcion": f"Diseño estático - {metrica}"
                    })
            
            for _, row in res_dinamico.metricas_conectividad.iterrows():
                for metrica in ['pc', 'iic', 'ec', 'corriente_total']:
                    DatabaseConnection.execute_non_query("""
                        INSERT INTO resultados_conectividad
                        (id_simulacion, año, metrica, valor, unidad, descripcion)
                        VALUES (:id_sim, :año, :metrica, :valor, :unidad, :descripcion)
                    """, {
                        "id_sim": id_simulacion,
                        "año": int(row['año']),
                        "metrica": f"dinamico_{metrica}",
                        "valor": float(row[metrica]),
                        "unidad": "adimensional" if metrica != 'corriente_total' else "A",
                        "descripcion": f"Diseño dinámico - {metrica}"
                    })
            
            logger.info(f"Simulación guardada: ID {id_simulacion}")
            return id_simulacion
            
        except Exception as e:
            logger.error(f"Error guardando simulación: {e}")
            return None
