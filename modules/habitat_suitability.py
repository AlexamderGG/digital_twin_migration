"""
Módulo de Modelos de Idoneidad de Hábitat
Gemelo Digital de Corredores de Migración

Implementa:
- Modelos MaxEnt-like, Regresión Logística y Random Forest
- Modelos Híbridos (Ensemble Voting y Stacking Neural Network)
- Generación de pseudo-ausencias
- Variables bioclimáticas derivadas
- Evaluación de modelos (AUC, TSS, Permutation Importance)
- Proyección de idoneidad espacial
"""

import logging
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, box
from scipy import stats
import joblib

# Scikit-Learn - Modelos Base
from sklearn.ensemble import RandomForestClassifier, VotingClassifier, StackingClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
# Scikit-Learn - Utilidades
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import roc_auc_score, roc_curve, confusion_matrix
from sklearn.preprocessing import StandardScaler
from sklearn.inspection import permutation_importance

from config import Config, DatabaseConnection

logger = logging.getLogger(__name__)


@dataclass
class HabitatModelResult:
    """Resultados de un modelo de hábitat"""
    id_modelo: Optional[int]
    especie: str
    algoritmo: str
    auc: float
    tss: float
    accuracy: float
    variables_importance: Dict[str, float]
    ruta_modelo: str
    ruta_raster: Optional[str] = None


class HabitatSuitabilityModeler:
    """Modelador de idoneidad de hábitat"""
    
    ALGORITMOS = {
        'random_forest': 'Random Forest',
        'logistic_regression': 'Regresión Logística',
        'maxent_like': 'MaxEnt-like (HistGB)',
        'ensemble_voting': 'Híbrido: Ensemble Voting',
        'stacking_spatial': 'Híbrido: Stacking Espacial'
    }
    
    def __init__(self, id_especie: int, algoritmo: str = 'random_forest'):
        self.id_especie = id_especie
        self.algoritmo = algoritmo
        self.model = None
        self.scaler = StandardScaler()
        self.variables = []
        self.metricas = {}
        self.importancia = {}
        
        # Obtener datos de la especie
        especie_data = DatabaseConnection.execute_query(
            "SELECT * FROM especies WHERE id_especie = :id",
            {"id": id_especie}
        )
        self.especie = especie_data[0] if especie_data else None
    
    def generar_pseudo_ausencias(self, gdf_presencias: gpd.GeoDataFrame,
                                  n_ausencias: int = None,
                                  buffer_distancia: float = 0.1) -> gpd.GeoDataFrame:
        """
        Genera pseudo-ausencias espacialmente alejadas de las presencias
        buffer_distancia en grados decimales (~11km)
        """
        if n_ausencias is None:
            n_ausencias = len(gdf_presencias) * 3
        
        # Obtener bounding box del área de estudio
        bounds = gdf_presencias.total_bounds
        minx, miny, maxx, maxy = bounds
        
        # Expandir ligeramente
        expand_x = (maxx - minx) * 0.3
        expand_y = (maxy - miny) * 0.3
        minx -= expand_x
        maxx += expand_x
        miny -= expand_y
        maxy += expand_y
        
        # Generar puntos aleatorios
        np.random.seed(42)
        puntos_generados = 0
        ausencias = []
        
        while puntos_generados < n_ausencias:
            lons = np.random.uniform(minx, maxx, n_ausencias * 2)
            lats = np.random.uniform(miny, maxy, n_ausencias * 2)
            
            for lon, lat in zip(lons, lats):
                if puntos_generados >= n_ausencias:
                    break
                
                punto = Point(lon, lat)
                
                # Verificar que esté lejos de presencias
                distancias = gdf_presencias.geometry.distance(punto)
                if distancias.min() > buffer_distancia:
                    ausencias.append({'geometry': punto, 'presencia': 0})
                    puntos_generados += 1
        
        gdf_ausencias = gpd.GeoDataFrame(ausencias, crs=gdf_presencias.crs)
        return gdf_ausencias
    
    def generar_variables_ambientales(self, gdf: gpd.GeoDataFrame,
                                      año: int = 2024) -> pd.DataFrame:
        """
        Genera variables ambientales para cada punto.
        En modo demo, genera variables bioclimáticas sintéticas realistas.
        En producción, se conectaría a WorldClim/CMIP6.
        """
        np.random.seed(hash(str(self.id_especie)) % 2**32)
        
        coords = np.array([(g.x, g.y) for g in gdf.geometry])
        lons = coords[:, 0]
        lats = coords[:, 1]
        
        # Gradientes latitudinales y longitudinales realistas
        base_temp = 30 - np.abs(lats) * 0.7  # Más frío en polos
        base_precip = 1000 + np.sin(lons * 0.05) * 500 + np.cos(lats * 0.03) * 300
        
        n = len(lons)
        ruido = lambda: np.random.normal(0, 1, n)
        
        variables = pd.DataFrame({
            'bio1_temp_media_anual': base_temp + ruido() * 2,
            'bio2_rango_medio_diurno': 8 + np.abs(lats) * 0.1 + ruido(),
            'bio3_isotermia': 0.3 + 0.005 * np.abs(lats) + ruido() * 0.02,
            'bio4_temp_estacionalidad': 500 + np.abs(lats) * 30 + ruido() * 50,
            'bio5_temp_max_mes_calido': base_temp + 5 + ruido(),
            'bio6_temp_min_mes_frio': base_temp - 10 - np.abs(lats) * 0.3 + ruido(),
            'bio7_rango_anual_temp': 15 + np.abs(lats) * 0.5 + ruido(),
            'bio12_precip_anual': np.clip(base_precip + ruido() * 100, 50, 8000),
            'bio13_precip_mes_mas_humedo': np.clip(base_precip / 8 + ruido() * 30, 10, 1000),
            'bio14_precip_mes_mas_seco': np.clip(base_precip / 24 + ruido() * 10, 0, 300),
            'bio15_precip_estacionalidad': 30 + ruido() * 10,
            'elevacion': np.clip(500 + np.sin(lons * 0.1) * 1000 + np.cos(lats * 0.08) * 800 + ruido() * 100, 0, 5000),
            'pendiente': np.clip(np.abs(ruido()) * 15, 0, 60),
            'distancia_agua': np.clip(np.abs(ruido()) * 5, 0, 50),
            'uso_suelo_resistencia': np.clip(0.2 + np.abs(ruido()) * 0.3, 0.01, 1)
        })
        
        # Ajuste por año (simular cambio climático)
        delta_año = año - 2020
        variables['bio1_temp_media_anual'] += delta_año * 0.02  # +0.02°C/año
        variables['bio4_temp_estacionalidad'] += delta_año * 2
        
        return variables
    
    def entrenar(self, test_size: float = 0.3) -> Optional[HabitatModelResult]:
        """Entrena el modelo de idoneidad de hábitat"""
        
        if self.especie is None:
            logger.error("Especie no encontrada")
            return None
        
        # Obtener presencias
        gdf_presencias = DatabaseConnection.read_geodataframe("""
            SELECT id_registro, latitud, longitud, certeza, ubicacion as geometria
            FROM registros_presencia
            WHERE id_especie = :id_especie AND certeza > 0.3
        """, params={"id_especie": self.id_especie})
        
        if len(gdf_presencias) < 10:
            logger.warning(f"Pocos registros ({len(gdf_presencias)}) para modelar")
            return None
        
        logger.info(f"Entrenando modelo con {len(gdf_presencias)} presencias")
        
        # Generar pseudo-ausencias
        gdf_ausencias = self.generar_pseudo_ausencias(gdf_presencias)
        
        # Combinar datos
        gdf_presencias['presencia'] = 1
        gdf_ausencias['presencia'] = 0
        
        gdf_completo = pd.concat([
            gdf_presencias[['geometry', 'presencia']],
            gdf_ausencias[['geometry', 'presencia']]
        ], ignore_index=True)
        
        # Generar variables ambientales
        X = self.generar_variables_ambientales(gdf_completo)
        y = gdf_completo['presencia'].values
        
        self.variables = list(X.columns)
        
        # Escalar variables
        X_scaled = self.scaler.fit_transform(X)
        
        # División train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Inicialización de Modelos Base
        rf = RandomForestClassifier(n_estimators=200, class_weight='balanced_subsample', random_state=42, n_jobs=-1)
        lr = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
        maxent_proxy = HistGradientBoostingClassifier(max_iter=100, random_state=42)

        # Seleccionar y ensamblar algoritmo
        if self.algoritmo == 'random_forest':
            self.model = rf
        elif self.algoritmo == 'logistic_regression':
            self.model = lr
        elif self.algoritmo == 'maxent_like':
            self.model = maxent_proxy
        elif self.algoritmo == 'ensemble_voting':
            self.model = VotingClassifier(
                estimators=[('rf', rf), ('lr', lr), ('me', maxent_proxy)],
                voting='soft'
            )
        elif self.algoritmo == 'stacking_spatial':
            self.model = StackingClassifier(
                estimators=[('rf', rf), ('me', maxent_proxy)],
                final_estimator=MLPClassifier(hidden_layer_sizes=(50,), max_iter=500, random_state=42),
                cv=5
            )
        else:
            self.model = rf
        
        # Entrenar
        self.model.fit(X_train, y_train)
        
        # Evaluar
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]
        y_pred = self.model.predict(X_test)
        
        auc = roc_auc_score(y_test, y_pred_proba)
        
        # Calcular TSS
        fpr, tpr, thresholds = roc_curve(y_test, y_pred_proba)
        tss = max(tpr - fpr)
        
        accuracy = self.model.score(X_test, y_test)
        
        self.metricas = {
            'auc': float(auc),
            'tss': float(tss),
            'accuracy': float(accuracy),
            'n_presencias': int((y == 1).sum()),
            'n_ausencias': int((y == 0).sum()),
            'variables': self.variables
        }
        
        # Importancia de variables mediante Permutación (Universal para modelos híbridos y de caja negra)
        importancia_raw = permutation_importance(self.model, X_test, y_test, n_repeats=5, random_state=42)
        importancias_vals = np.abs(importancia_raw.importances_mean)
        
        # Normalizar
        total_imp = importancias_vals.sum()
        if total_imp > 0:
            importancias_vals = importancias_vals / total_imp
            
        self.importancia = dict(zip(self.variables, [float(v) for v in importancias_vals]))
        
        logger.info(f"Modelo entrenado - AUC: {auc:.4f}, TSS: {tss:.4f}")
        
        # Guardar modelo físico
        ruta_modelo = Config.OUTPUTS_DIR / f"modelo_habitat_{self.id_especie}_{self.algoritmo}.pkl"
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'variables': self.variables,
            'metricas': self.metricas,
            'importancia': self.importancia,
            'id_especie': self.id_especie
        }, ruta_modelo)
        
        # Guardar en base de datos
        query = """
            INSERT INTO modelos_habitat
            (id_especie, nombre, algoritmo, variables_predictoras, rendimiento,
             ruta_modelo, año_entrenamiento, parametros)
            VALUES (:id_especie, :nombre, :algoritmo, :variables, :rendimiento,
                    :ruta_modelo, :año, :parametros)
            RETURNING id_modelo
        """
        results = DatabaseConnection.execute_query(query, {
            "id_especie": self.id_especie,
            "nombre": f"Modelo {self.especie['nombre_cientifico']} - {self.algoritmo}",
            "algoritmo": self.ALGORITMOS.get(self.algoritmo, self.algoritmo),
            "variables": self.variables,
            "rendimiento": json.dumps(self.metricas),
            "ruta_modelo": str(ruta_modelo),
            "año": 2024,
            "parametros": json.dumps({"algoritmo": self.algoritmo, "test_size": test_size})
        })
        
        id_modelo = results[0]['id_modelo'] if results else None
        
        return HabitatModelResult(
            id_modelo=id_modelo,
            especie=self.especie['nombre_cientifico'],
            algoritmo=self.algoritmo,
            auc=auc,
            tss=tss,
            accuracy=accuracy,
            variables_importance=self.importancia,
            ruta_modelo=str(ruta_modelo)
        )
    
    def predecir_idoneidad(self, gdf_puntos: gpd.GeoDataFrame,
                           año: int = 2024) -> np.ndarray:
        """Predice idoneidad de hábitat para puntos dados"""
        if self.model is None:
            raise ValueError("Modelo no entrenado. Llame a entrenar() primero.")
        
        X = self.generar_variables_ambientales(gdf_puntos, año=año)
        X = X[self.variables]  # Asegurar orden correcto
        X_scaled = self.scaler.transform(X)
        
        return self.model.predict_proba(X_scaled)[:, 1]
    
    def generar_mapa_idoneidad(self, bounds: Tuple[float, float, float, float],
                               resolucion: float = 0.1,
                               año: int = 2024) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Genera un mapa raster de idoneidad
        Returns: (lons_grid, lats_grid, idoneidad_grid)
        """
        minx, miny, maxx, maxy = bounds
        
        # Crear grilla
        lons = np.arange(minx, maxx, resolucion)
        lats = np.arange(miny, maxy, resolucion)
        lons_grid, lats_grid = np.meshgrid(lons, lats)
        
        # Crear puntos
        puntos = [Point(lon, lat) for lon, lat in zip(lons_grid.ravel(), lats_grid.ravel())]
        gdf = gpd.GeoDataFrame({'geometry': puntos}, crs=Config.DEFAULT_CRS)
        
        # Predecir
        idoneidad = self.predecir_idoneidad(gdf, año=año)
        idoneidad_grid = idoneidad.reshape(lons_grid.shape)
        
        return lons_grid, lats_grid, idoneidad_grid