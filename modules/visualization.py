# -*- coding: utf-8 -*-
"""
Módulo de Visualización y Mapas Interactivos
Gemelo Digital de Corredores de Migración
"""
import logging
from typing import Optional, Dict, List, Tuple, Any
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import folium
from folium import plugins
from shapely.geometry import Point
from config import Config

logger = logging.getLogger(__name__)

sns.set_style("whitegrid")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 10

PALETA_CONECTIVIDAD = {
    'estatico': '#E74C3C',
    'dinamico': '#27AE60',
    'SSP1-2.6': '#3498DB',
    'SSP2-4.5': '#F39C12',
    'SSP5-8.5': '#C0392B'
}


class MapVisualizer:
    """Generador de mapas interactivos con Folium"""

    @staticmethod
    def crear_mapa_base(centro: Tuple[float, float] = (-5, -72),
                        zoom: int = 5) -> folium.Map:
        """Crea mapa base con capas seguras"""
        # ✅ Mapa base con dimensiones y comportamiento estable
        mapa = folium.Map(
            location=centro,
            zoom_start=zoom,
            tiles='OpenStreetMap',
            control_scale=True,
            width='100%',
            height='100%'
        )

        # ✅ Capa OpenTopoMap (verificada)
        try:
            folium.TileLayer(
                tiles='https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
                name='Mapa Topográfico',
                attr='OpenTopoMap',
                max_zoom=17
            ).add_to(mapa)
        except Exception as e:
            logger.warning("No se pudo cargar capa OpenTopoMap: %s", e)

        # ✅ CORREGIDO: URL Satelital Google con subdominio y parámetros completos
        try:
            folium.TileLayer(
                tiles='https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
                name='Imagen Satelital',
                attr='Google',
                subdomains=['mt0', 'mt1', 'mt2', 'mt3'],
                max_zoom=20
            ).add_to(mapa)
        except Exception as e:
            logger.warning("No se pudo cargar capa satelital Google: %s", e)

        # ✅ Capa alternativa segura en caso de fallo
        try:
            folium.TileLayer(
                tiles='OpenStreetMap',
                name='Oscuro'
            ).add_to(mapa)
        except Exception as e:
            logger.warning("No se pudo cargar capa oscura: %s", e)

        return mapa
    
    @staticmethod
    def agregar_telemetria(mapa, gdf):
        """
        Agrega trayectorias de telemetría (GPS tracking) al mapa base de Folium.
        Conecta los puntos secuenciales creando líneas de movimiento por individuo.
        """
        import folium
        
        if gdf.empty:
            return mapa
            
        # Asegurarnos de que el DataFrame esté ordenado cronológicamente por individuo
        if 'fecha_hora' in gdf.columns:
            gdf = gdf.sort_values(by=['id_individuo', 'fecha_hora'])
            
        # Crear un grupo de capas para poder encenderlo/apagarlo
        feature_group = folium.FeatureGroup(name="Trayectorias GPS")
        
        # Paleta de colores para diferenciar distintos animales
        colores = ['#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231', 
                   '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4']
        
        individuos = gdf['id_individuo'].unique()
        
        for i, individuo in enumerate(individuos):
            color = colores[i % len(colores)]
            datos_ind = gdf[gdf['id_individuo'] == individuo]
            
            # Extraer lista de coordenadas (latitud, longitud) para la línea
            coordenadas = [(row.geometry.y, row.geometry.x) for idx, row in datos_ind.iterrows()]
            
            # Trazar la línea de trayectoria si el animal tiene más de 1 punto de registro
            if len(coordenadas) > 1:
                folium.PolyLine(
                    locations=coordenadas,
                    color=color,
                    weight=3,
                    opacity=0.8,
                    tooltip=f"Individuo: {individuo} ({len(coordenadas)} puntos)"
                ).add_to(feature_group)
                
            # Agregar un marcador circular para cada punto exacto registrado
            for idx, row in datos_ind.iterrows():
                fecha_str = str(row['fecha_hora']) if 'fecha_hora' in row else 'Fecha desconocida'
                folium.CircleMarker(
                    location=(row.geometry.y, row.geometry.x),
                    radius=4,
                    color=color,
                    fill=True,
                    fill_opacity=0.7,
                    tooltip=f"Ind: {individuo}<br>Fecha: {fecha_str}"
                ).add_to(feature_group)
                
        feature_group.add_to(mapa)
        return mapa

    @staticmethod
    def agregar_registros_presencia(mapa: folium.Map, gdf: gpd.GeoDataFrame,
                                    nombre_capa: str = "Registros",
                                    color: str = '#E74C3C') -> folium.Map:
        if gdf is None or len(gdf) == 0:
            logger.info("Sin registros de presencia para dibujar")
            return mapa

        grupo = folium.FeatureGroup(name=nombre_capa)
        for _, row in gdf.iterrows():
            geom = getattr(row, 'geometry', None)
            if geom is None or geom.is_empty:
                continue
            try:
                folium.CircleMarker(
                    location=[geom.y, geom.x],
                    radius=4,
                    color=color,
                    fill=True,
                    fill_opacity=0.7,
                    popup=f"Fecha: {row.get('fecha_observacion', 'N/A')}<br>Fuente: {row.get('fuente', 'N/A')}"
                ).add_to(grupo)
            except Exception as e:
                logger.debug("Error dibujando registro: %s", e)
        grupo.add_to(mapa)
        return mapa

    @staticmethod
    def agregar_uso_suelo(mapa: folium.Map, gdf: gpd.GeoDataFrame,
                          nombre_capa: str = "Uso del Suelo") -> folium.Map:
        if gdf is None or len(gdf) == 0:
            return mapa

        colores_clase = {
            'bosque humedo': '#228B22', 'bosque seco': '#9ACD32',
            'matorral': '#DAA520', 'sabana': '#F4A460',
            'pastizal': '#90EE90', 'agricultura': '#FFD700',
            'urbano': '#808080', 'agua': '#4169E1',
            'desierto': '#DEB887'
        }
        grupo = folium.FeatureGroup(name=nombre_capa)
        for _, row in gdf.iterrows():
            clase = str(row.get('clase_uso', 'desconocido')).lower()
            color = colores_clase.get(clase, '#A9A9A9')
            geom = getattr(row, 'geometry', None)
            if geom is None:
                continue
            try:
                folium.GeoJson(
                    geom.__geo_interface__,
                    style_function=lambda x, c=color: {
                        'fillColor': c, 'color': c,
                        'weight': 0.5, 'fillOpacity': 0.6
                    },
                    tooltip=f"Uso: {row.get('clase_uso', 'N/A')}"
                ).add_to(grupo)
            except Exception as e:
                logger.debug("Error dibujando uso de suelo: %s", e)
        grupo.add_to(mapa)
        return mapa

    @staticmethod
    def agregar_capa_resistencia(mapa: folium.Map, gdf: gpd.GeoDataFrame,
                                  nombre_capa: str = "Resistencia") -> folium.Map:
        if gdf is None or len(gdf) == 0:
            return mapa

        grupo = folium.FeatureGroup(name=nombre_capa)
        resistencia = gdf.get('resistencia', pd.Series([1.0] * len(gdf))).fillna(1.0).values
        min_r, max_r = resistencia.min(), resistencia.max()
        rango = max_r - min_r if max_r != min_r else 1e-8
        resistencia_norm = (resistencia - min_r) / rango
        cmap = plt.get_cmap('RdYlGn_r')

        for idx, (_, row) in enumerate(gdf.iterrows()):
            geom = getattr(row, 'geometry', None)
            if geom is None:
                continue
            color = mcolors.to_hex(cmap(np.clip(resistencia_norm[idx], 0, 1)))
            try:
                folium.GeoJson(
                    geom.__geo_interface__,
                    style_function=lambda x, c=color: {
                        'fillColor': c, 'color': c,
                        'weight': 0, 'fillOpacity': 0.55
                    },
                    tooltip=f"Resistencia: {resistencia[idx]:.2f}"
                ).add_to(grupo)
            except Exception as e:
                logger.debug("Error dibujando resistencia: %s", e)
        grupo.add_to(mapa)
        return mapa

    @staticmethod
    def agregar_corredores(mapa: folium.Map, gdf: gpd.GeoDataFrame,
                           nombre_capa: str = "Corredores",
                           color: str = '#8E44AD') -> folium.Map:
        if gdf is None or len(gdf) == 0:
            return mapa

        grupo = folium.FeatureGroup(name=nombre_capa)
        cmap = plt.get_cmap('plasma')

        for _, row in gdf.iterrows():
            geom = getattr(row, 'geometry', None)
            if geom is None or not hasattr(geom, 'coords'):
                continue

            importancia = float(row.get('importancia', 0.5) or 0.5)
            importancia = max(0.0, min(1.0, importancia))
            grosor = 1 + importancia * 5
            corriente = float(row.get('corriente_norm', importancia) or importancia)
            corriente = max(0.0, min(1.0, corriente))
            color_linea = mcolors.to_hex(cmap(corriente))

            try:
                coords = [(y, x) for x, y in geom.coords]
                folium.PolyLine(
                    coords,
                    color=color_linea,
                    weight=grosor,
                    opacity=0.7,
                    popup=(
                        f"Importancia: {importancia:.3f}<br>"
                        f"Dist: {row.get('distancia_km', 0):.1f} km"
                    )
                ).add_to(grupo)
            except Exception as e:
                logger.debug("Error dibujando corredor: %s", e)
        grupo.add_to(mapa)
        return mapa

    @staticmethod
    def agregar_parches(mapa: folium.Map, gdf: gpd.GeoDataFrame,
                        nombre_capa: str = "Parches") -> folium.Map:
        if gdf is None or len(gdf) == 0:
            return mapa

        grupo = folium.FeatureGroup(name=nombre_capa)
        calidades = gdf.get('calidad_habitat', pd.Series([0.5] * len(gdf))).fillna(0.5).values
        calidades = np.clip(calidades, 0.0, 1.0)
        cmap = plt.get_cmap('YlGn')

        for idx, (_, row) in enumerate(gdf.iterrows()):
            geom = getattr(row, 'geometry', None)
            if geom is None:
                continue
            calidad = calidades[idx]
            color = mcolors.to_hex(cmap(calidad))
            try:
                folium.GeoJson(
                    geom.__geo_interface__,
                    style_function=lambda x, c=color: {
                        'fillColor': c, 'color': '#2E7D32',
                        'weight': 1.5, 'fillOpacity': 0.7
                    },
                    tooltip=(
                        f"Calidad: {calidad:.2f}<br>"
                        f"Área: {row.get('area_km2', 0):.1f} km²"
                    )
                ).add_to(grupo)
            except Exception as e:
                logger.debug("Error dibujando parche: %s", e)
        grupo.add_to(mapa)
        return mapa

    @staticmethod
    def agregar_control_capas(mapa: folium.Map) -> folium.Map:
        folium.LayerControl(collapsed=True).add_to(mapa)
        try:
            plugins.MiniMap(tile_layer='OpenStreetMap', position='bottomright').add_to(mapa)
        except Exception as e:
            logger.warning("MiniMapa no disponible: %s", e)
        folium.plugins.Fullscreen(position='topright').add_to(mapa)
        return mapa


class ChartGenerator:
    """Generador de gráficos estadísticos"""

    @staticmethod
    def comparar_conectividad_temporal(df_estatico: pd.DataFrame,
                                        df_dinamico: pd.DataFrame,
                                        metrica: str = 'pc') -> go.Figure:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_estatico['año'], y=df_estatico[metrica],
            mode='lines+markers', name='Diseño Estático',
            line=dict(color=PALETA_CONECTIVIDAD['estatico'], width=3)
        ))
        fig.add_trace(go.Scatter(
            x=df_dinamico['año'], y=df_dinamico[metrica],
            mode='lines+markers', name='Diseño Dinámico',
            line=dict(color=PALETA_CONECTIVIDAD['dinamico'], width=3),
            fill='tonexty'
        ))
        nombres = {
            'pc': 'Probabilidad de Conectividad (PC)',
            'iic': 'Índice Integral de Conectividad (IIC)',
            'ec': 'Conectividad Equivalente (EC)'
        }
        fig.update_layout(
            title=f"Evolución de {nombres.get(metrica, metrica)}",
            xaxis_title="Año", yaxis_title=nombres.get(metrica, metrica),
            hovermode='x unified', template='plotly_white', height=450
        )
        return fig

    @staticmethod
    def barras_mejora(mejoras: Dict[str, float]) -> go.Figure:
        escenarios = list(mejoras.keys())
        valores = list(mejoras.values())
        colores = [PALETA_CONECTIVIDAD.get(e, '#333') for e in escenarios]
        fig = go.Figure(go.Bar(
            x=escenarios, y=valores, marker_color=colores,
            text=[f"{v:.1f}%" for v in valores], textposition='auto'
        ))
        fig.add_hline(
            y=25, line_dash="dash", line_color="red",
            annotation_text="Umbral hipótesis (25%)"
        )
        fig.update_layout(
            title="Mejora en Conectividad: Dinámico vs Estático",
            xaxis_title="Escenario Climático", yaxis_title="Mejora (%)",
            template='plotly_white', height=400
        )
        return fig

    @staticmethod
    def importancia_variables(importancia: Dict[str, float]) -> go.Figure:
        items = sorted(importancia.items(), key=lambda x: x[1], reverse=True)
        fig = go.Figure(go.Bar(
            x=[x[1] for x in items], y=[x[0] for x in items],
            orientation='h', marker_color='teal'
        ))
        fig.update_layout(
            title="Importancia de Variables", xaxis_title="Importancia",
            yaxis_title="Variable", template='plotly_white',
            height=max(400, len(items) * 30), yaxis=dict(autorange="reversed")
        )
        return fig

    @staticmethod
    def resumen_datos(resumen: Dict[str, Any]) -> go.Figure:
        mapeo = {
            'total_especies': 'Especies', 'total_registros': 'Registros',
            'total_telemetria': 'Telemetría', 'total_uso_suelo': 'Uso Suelo',
            'total_simulaciones': 'Simulaciones', 'total_usuarios': 'Usuarios'
        }
        cats = [mapeo[k] for k in mapeo if k in resumen]
        vals = [resumen[k] for k in mapeo if k in resumen]
        fig = go.Figure(go.Bar(x=cats, y=vals, text=vals, textposition='auto'))
        fig.update_layout(title="Resumen de Datos", template='plotly_white', height=400)
        return fig

    @staticmethod
    def radar_metricas(metricas_estatico: Dict[str, float],
                       metricas_dinamico: Dict[str, float]) -> go.Figure:
        categorias = list(metricas_estatico.keys())
        vals_est = list(metricas_estatico.values())
        vals_din = list(metricas_dinamico.values())
        max_val = max((*vals_est, *vals_din, 1e-8))

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=[v / max_val for v in vals_est], theta=categorias,
            fill='toself', name='Estático', line_color=PALETA_CONECTIVIDAD['estatico']
        ))
        fig.add_trace(go.Scatterpolar(
            r=[v / max_val for v in vals_din], theta=categorias,
            fill='toself', name='Dinámico', line_color=PALETA_CONECTIVIDAD['dinamico']
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            title="Comparación Multidimensional", template='plotly_white', height=450
        )
        return fig