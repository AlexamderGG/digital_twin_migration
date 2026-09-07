"""
Módulo de Teoría de Circuitos y Conectividad Funcional
Gemelo Digital de Corredores de Migración

Implementa:
- Construcción de grafos de paisaje
- Cálculo de resistencia efectiva (Circuit Theory)
- Corriente entre parches (flujo de movimiento)
- Métricas de conectividad: PC, IIC, EC
- Identificación de corredores mediante centralidad
"""

import logging
import json
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
from scipy import sparse
from scipy.sparse.linalg import spsolve
import networkx as nx

from config import Config, DatabaseConnection

logger = logging.getLogger(__name__)


@dataclass
class ConnectivityResult:
    """Resultados de análisis de conectividad"""
    pc: float  # Probabilidad de Conectividad
    iic: float  # Índice Integral de Conectividad
    ec: float  # Conectividad Equivalente
    corriente_total: float
    parches_importantes: List[Dict[str, Any]]
    enlaces_importantes: List[Dict[str, Any]]


class LandscapeGraph:
    """Grafo de paisaje para teoría de circuitos"""
    
    def __init__(self, id_especie: int = None):
        self.id_especie = id_especie
        self.G = nx.Graph()
        self.parches = []
        self.matriz_laplaciana = None
        self.nodos = []
    
    def construir_desde_parches(self, gdf_parches: gpd.GeoDataFrame,
                                gdf_resistencia: Optional[gpd.GeoDataFrame] = None,
                                distancia_max: float = 100.0):
        """
        Construye grafo conectando parches cercanos
        
        Args:
            gdf_parches: GeoDataFrame con geometría de parches y calidad
            gdf_resistencia: GeoDataFrame con valores de resistencia
            distancia_max: distancia máxima de conexión en km
        """
        logger.info(f"Construyendo grafo con {len(gdf_parches)} parches")
        
        # Convertir a CRS proyectado para distancias
        gdf_parches = gdf_parches.copy()
        if gdf_parches.crs is None or gdf_parches.crs == 'EPSG:4326':
            gdf_parches_m = gdf_parches.to_crs('EPSG:6933')
        else:
            gdf_parches_m = gdf_parches
        
        # Calcular centroides
        centroides = gdf_parches_m.geometry.centroid
        calidades = gdf_parches.get('calidad_habitat', pd.Series([1.0] * len(gdf_parches))).values
        
        # Agregar nodos
        self.nodos = list(range(len(gdf_parches)))
        for i, (idx, row) in enumerate(gdf_parches.iterrows()):
            geom = row.geometry
            area = float(gdf_parches_m.iloc[i].geometry.area) / 1e6  # km²
            calidad = float(calidades[i]) if i < len(calidades) else 1.0
            
            self.G.add_node(i,
                           id_parche=row.get('id_parche', i),
                           area=area,
                           calidad=calidad,
                           atributo=area * calidad,  # Atributo del parche
                           x=centroides.iloc[i].x,
                           y=centroides.iloc[i].y,
                           geom_original=geom)
        
        # Conectar nodos cercanos
        coords = np.array([(c.x, c.y) for c in centroides])
        
        for i in range(len(self.nodos)):
            for j in range(i + 1, len(self.nodos)):
                dx = coords[i, 0] - coords[j, 0]
                dy = coords[i, 1] - coords[j, 1]
                dist_m = np.sqrt(dx**2 + dy**2)
                dist_km = dist_m / 1000
                
                if dist_km <= distancia_max:
                    # Resistencia base proporcional a la distancia
                    resistencia_base = dist_km
                    
                    # Ajustar por resistencia del paisaje si está disponible
                    if gdf_resistencia is not None:
                        linea = LineString([centroides.iloc[i], centroides.iloc[j]])
                        resistencia_promedio = self._calcular_resistencia_linea(linea, gdf_resistencia)
                        resistencia = resistencia_base * resistencia_promedio
                    else:
                        resistencia = resistencia_base
                    
                    # Conductancia = 1 / resistencia
                    conductancia = 1.0 / max(resistencia, 0.001)
                    
                    self.G.add_edge(i, j,
                                   distancia_km=dist_km,
                                   resistencia=resistencia,
                                   conductancia=conductancia)
        
        logger.info(f"Grafo construido: {self.G.number_of_nodes()} nodos, "
                   f"{self.G.number_of_edges()} enlaces")
    
    @staticmethod
    def _calcular_resistencia_linea(linea: LineString, 
                                    gdf_resistencia: gpd.GeoDataFrame) -> float:
        """Calcula resistencia promedio a lo largo de una línea"""
        intersecciones = gdf_resistencia[gdf_resistencia.intersects(linea)]
        if len(intersecciones) == 0:
            return 1.0
        
        resistencias = []
        longitudes = []
        
        for _, row in intersecciones.iterrows():
            interseccion = linea.intersection(row.geometry)
            if not interseccion.is_empty:
                long = interseccion.length
                if long > 0:
                    resistencias.append(float(row.get('resistencia', 1.0)))
                    longitudes.append(long)
        
        if not longitudes:
            return 1.0
        
        total_long = sum(longitudes)
        return sum(r * l / total_long for r, l in zip(resistencias, longitudes))
    
    def construir_matriz_laplaciana(self):
        """Construye matriz laplaciana para teoría de circuitos"""
        n = self.G.number_of_nodes()
        nodos = list(self.G.nodes())
        node_idx = {nodo: i for i, nodo in enumerate(nodos)}
        
        L = sparse.lil_matrix((n, n))
        
        for u, v, data in self.G.edges(data=True):
            i, j = node_idx[u], node_idx[v]
            cond = data['conductancia']
            L[i, i] += cond
            L[j, j] += cond
            L[i, j] -= cond
            L[j, i] -= cond
        
        self.matriz_laplaciana = L.tocsr()
        return self.matriz_laplaciana
    
    def calcular_corriente(self, nodos_fuente: List[int], 
                          nodos_sumidero: List[int]) -> Dict[Tuple[int, int], float]:
        """
        Calcula corriente entre conjuntos de nodos fuente y sumidero
        usando teoría de circuitos (McRae et al.)
        """
        if self.matriz_laplaciana is None:
            self.construir_matriz_laplaciana()
        
        n = self.G.number_of_nodes()
        nodos = list(self.G.nodes())
        node_idx = {nodo: i for i, nodo in enumerate(nodos)}
        
        # Construir vector de inyección de corriente
        I = np.zeros(n)
        corriente_total = 1.0
        
        for nodo in nodos_fuente:
            if nodo in node_idx:
                I[node_idx[nodo]] = corriente_total / len(nodos_fuente)
        
        for nodo in nodos_sumidero:
            if nodo in node_idx:
                I[node_idx[nodo]] = -corriente_total / len(nodos_sumidero)
        
        # Resolver sistema L * V = I (eliminando nodo de referencia)
        nodos_internos = list(range(1, n))
        L_reducida = self.matriz_laplaciana[np.ix_(nodos_internos, nodos_internos)]
        I_reducida = I[nodos_internos]
        
        V = np.zeros(n)
        try:
            V[nodos_internos] = spsolve(L_reducida, I_reducida)
        except Exception:
            # Usar solución de mínimos cuadrados si es singular
            from scipy.sparse.linalg import lsqr
            result = lsqr(L_reducida, I_reducida)
            V[nodos_internos] = result[0]
        
        # Calcular corriente en cada enlace
        corrientes = {}
        for u, v, data in self.G.edges(data=True):
            i, j = node_idx[u], node_idx[v]
            voltaje_diff = abs(V[i] - V[j])
            corriente = voltaje_diff * data['conductancia']
            corrientes[(u, v)] = corriente
        
        return corrientes
    
    def calcular_metricas_conectividad(self) -> ConnectivityResult:
        """
        Calcula métricas de conectividad:
        - PC: Probability of Connectivity
        - IIC: Integral Index of Connectivity
        - EC: Equivalent Connectivity
        """
        n = self.G.number_of_nodes()
        if n == 0:
            return ConnectivityResult(0, 0, 0, 0, [], [])
        
        nodos = list(self.G.nodes())
        atributos = np.array([self.G.nodes[n]['atributo'] for n in nodos])
        total_atributo = atributos.sum()
        
        # Calcular distancias efectivas (resistencia efectiva)
        self.construir_matriz_laplaciana()
        
        # IIC - Índice Integral de Conectividad
        # IIC = sum(ai * aj / (1 + nlij)) / AL^2
        # donde nlij = número de enlaces en el camino más corto
        iic_numerador = 0.0
        pc_numerador = 0.0
        
        # Caminos más cortos por resistencia
        try:
            caminos = dict(nx.all_pairs_dijkstra_path_length(
                self.G, weight='resistencia'
            ))
        except Exception:
            caminos = {}
        
        for i, ni in enumerate(nodos):
            ai = atributos[i]
            for j, nj in enumerate(nodos):
                aj = atributos[j]
                
                if ni in caminos and nj in caminos[ni]:
                    res_efectiva = caminos[ni][nj]
                    # Probabilidad de conexión (decaimiento exponencial)
                    pij = np.exp(-res_efectiva / 50.0)  # distancia media 50km
                    nlij = max(1, res_efectiva / 10.0)  # normalizar
                else:
                    pij = 0.0
                    nlij = float('inf')
                
                pc_numerador += ai * aj * pij
                
                if nlij != float('inf'):
                    iic_numerador += ai * aj / (1 + nlij)
        
        denominador = total_atributo ** 2 if total_atributo > 0 else 1
        
        pc = pc_numerador / denominador
        iic = iic_numerador / denominador
        ec = np.sqrt(pc_numerador)  # Conectividad equivalente
        
        # Corriente total (promedio entre pares de parches principales)
        corrientes = self.calcular_corriente(
            nodos_fuente=[nodos[0]] if nodos else [],
            nodos_sumidero=[nodos[-1]] if len(nodos) > 1 else []
        )
        corriente_total = sum(corrientes.values())
        
        # Importancia de parches (PageRank)
        try:
            pagerank = nx.pagerank(self.G, weight='conductancia')
            parches_ordenados = sorted(
                pagerank.items(), key=lambda x: x[1], reverse=True
            )[:10]
        except Exception:
            parches_ordenados = []
        
        parches_importantes = [
            {"nodo": n, "importancia": float(v),
             "area": float(self.G.nodes[n]['area']),
             "calidad": float(self.G.nodes[n]['calidad'])}
            for n, v in parches_ordenados
        ]
        
        # Enlaces importantes por corriente
        enlaces_ordenados = sorted(
            corrientes.items(), key=lambda x: x[1], reverse=True
        )[:20]
        
        enlaces_importantes = [
            {"nodo_origen": e[0], "nodo_destino": e[1],
             "corriente": float(c),
             "distancia_km": float(self.G.edges[e]['distancia_km'])}
            for e, c in enlaces_ordenados
        ]
        
        return ConnectivityResult(
            pc=float(pc),
            iic=float(iic),
            ec=float(ec),
            corriente_total=float(corriente_total),
            parches_importantes=parches_importantes,
            enlaces_importantes=enlaces_importantes
        )
    
    def identificar_corredores(self, umbral_corriente: float = 0.05) -> gpd.GeoDataFrame:
        """Identifica corredores basados en la corriente del circuito"""
        # GeoDataFrame vacío (forma robusta compatible con todas las versiones)
        gdf_vacio = gpd.GeoDataFrame(geometry=[], crs=Config.DEFAULT_CRS)
        
        if self.G.number_of_edges() == 0:
            return gdf_vacio
        
        # Calcular corriente entre parches principales
        nodos = sorted(self.G.nodes(), 
                      key=lambda n: self.G.nodes[n]['atributo'], 
                      reverse=True)
        
        if len(nodos) < 2:
            return gdf_vacio
        
        corrientes = self.calcular_corriente(
            nodos_fuente=nodos[:max(1, len(nodos)//4)],
            nodos_sumidero=nodos[-max(1, len(nodos)//4):]
        )
        
        # Filtrar enlaces con alta corriente
        corredores = []
        max_corriente = max(corrientes.values()) if corrientes else 1
        
        for (u, v), corriente in corrientes.items():
            if corriente >= umbral_corriente * max_corriente:
                x1, y1 = self.G.nodes[u]['x'], self.G.nodes[u]['y']
                x2, y2 = self.G.nodes[v]['x'], self.G.nodes[v]['y']
                
                # Convertir de vuelta a EPSG:4326
                from pyproj import Transformer
                transformer = Transformer.from_crs('EPSG:6933', 'EPSG:4326', always_xy=True)
                lon1, lat1 = transformer.transform(x1, y1)
                lon2, lat2 = transformer.transform(x2, y2)
                
                linea = LineString([(lon1, lat1), (lon2, lat2)])
                
                corredores.append({
                    'geometry': linea,
                    'nodo_origen': u,
                    'nodo_destino': v,
                    'corriente': float(corriente),
                    'corriente_norm': float(corriente / max_corriente),
                    'distancia_km': float(self.G.edges[u, v]['distancia_km']),
                    'resistencia': float(self.G.edges[u, v]['resistencia']),
                    'importancia': float(corriente / max_corriente)
                })
        
        if not corredores:
            return gdf_vacio
        
        # Forma ROBUSTA: extraer geometrías y atributos por separado
        geometrias = [item.pop('geometry') for item in corredores]
        gdf = gpd.GeoDataFrame(corredores, geometry=geometrias, crs=Config.DEFAULT_CRS)
        return gdf


class ResistanceLayer:
    """Generador y gestor de capas de resistencia del paisaje"""
    
    # Pesos por defecto para tipos de uso del suelo
    PESOS_USO_SUELO = {
        'bosque_humedo': 1.0,
        'bosque_seco': 1.5,
        'matorral': 2.0,
        'sabana': 2.5,
        'pastizal': 3.0,
        'agricultura': 5.0,
        'urbano': 10.0,
        'agua': 8.0,
        'desierto': 7.0,
        'nieve_hielo': 15.0
    }
    
    @classmethod
    def generar_capa_resistencia(cls, gdf_uso_suelo: gpd.GeoDataFrame,
                                 idoneidad_array: Optional[np.ndarray] = None,
                                 peso_idoneidad: float = 0.3) -> gpd.GeoDataFrame:
        """
        Genera capa de resistencia combinando uso del suelo e idoneidad
        
        Resistencia = (1 - peso_idoneidad) * R_uso_suelo + peso_idoneidad * (1 - idoneidad)
        """
        gdf = gdf_uso_suelo.copy()
        
        # Resistencia por uso del suelo
        gdf['resistencia_uso'] = gdf['clase_uso'].map(
            lambda c: cls.PESOS_USO_SUELO.get(str(c).lower().replace(' ', '_'), 3.0)
        )
        
        # Normalizar
        max_resistencia = gdf['resistencia_uso'].max()
        gdf['resistencia_uso_norm'] = gdf['resistencia_uso'] / max_resistencia
        
        # Combinar con idoneidad si está disponible
        if idoneidad_array is not None and len(idoneidad_array) == len(gdf):
            gdf['idoneidad'] = np.clip(idoneidad_array, 0, 1)
            gdf['resistencia'] = (
                (1 - peso_idoneidad) * gdf['resistencia_uso_norm'] +
                peso_idoneidad * (1 - gdf['idoneidad'])
            )
        else:
            gdf['resistencia'] = gdf['resistencia_uso_norm']
        
        # Escalar a rango 1-10
        gdf['resistencia'] = 1 + 9 * gdf['resistencia']
        
        return gdf
    
    @classmethod
    def calibracion_empirica(cls, gdf_resistencia: gpd.GeoDataFrame,
                            gdf_telemetria: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """
        Calibra la capa de resistencia usando datos de telemetría.
        Ajusta resistencias basadas en el uso real del paisaje por los animales.
        """
        if len(gdf_telemetria) < 10:
            logger.warning("Pocos datos de telemetría para calibración")
            return gdf_resistencia
        
        gdf = gdf_resistencia.copy()
        
        # Calcular uso observado vs esperado
        uso_observado = np.zeros(len(gdf))
        
        for _, punto in gdf_telemetria.iterrows():
            intersecciones = gdf[gdf.intersects(punto.geometry)]
            for idx in intersecciones.index:
                uso_observado[idx] += 1
        
        # Calcular factor de calibración
        uso_esperado = gdf.geometry.area.values
        uso_esperado = uso_esperado / uso_esperado.sum() * uso_observado.sum()
        
        # Evitar división por cero
        uso_esperado = np.maximum(uso_esperado, 0.01)
        
        # Ratio de selección (uso observado / esperado)
        ratio_seleccion = uso_observado / uso_esperado
        
        # Ajustar resistencia: alta selección = baja resistencia
        # Usar función logarítmica para suavizar
        factor_ajuste = 1.0 / (1.0 + 0.5 * np.log1p(ratio_seleccion))
        
        gdf['uso_observado'] = uso_observado
        gdf['ratio_seleccion'] = ratio_seleccion
        gdf['resistencia_original'] = gdf['resistencia']
        gdf['resistencia'] = np.clip(
            gdf['resistencia'] * factor_ajuste,
            0.1, 10.0
        )
        
        logger.info("Calibración empírica completada")
        return gdf
