"""
Módulo de Configuración y Conexión a Base de Datos
Gemelo Digital de Corredores de Migración
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
import geopandas as gpd
import pandas as pd

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / '.env'
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()  # Buscar en ubicaciones estándar


class Config:
    """Clase de configuración centralizada"""
    
    # --- Base de Datos ---
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'digital_twin_migration')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
    
    # --- Seguridad ---
    SECRET_KEY = os.getenv('SECRET_KEY', 'clave_secreta_desarrollo_cambiar_en_produccion')
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '1440'))
    
    # --- Aplicación ---
    APP_NAME = os.getenv('APP_NAME', 'Gemelo Digital de Corredores de Migración')
    APP_VERSION = os.getenv('APP_VERSION', '1.0.0')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # --- Directorios ---
    DATA_DIR = Path(os.getenv('DATA_DIR', str(BASE_DIR / 'data')))
    OUTPUTS_DIR = Path(os.getenv('OUTPUTS_DIR', str(BASE_DIR / 'outputs')))
    TEMP_DIR = Path(os.getenv('TEMP_DIR', str(BASE_DIR / 'temp')))
    
    # --- Geoespacial ---
    DEFAULT_CRS = os.getenv('DEFAULT_CRS', 'EPSG:4326')
    
    # --- Parámetros de simulación ---
    DEFAULT_YEAR_START = int(os.getenv('DEFAULT_YEAR_START', '2024'))
    DEFAULT_YEAR_END = int(os.getenv('DEFAULT_YEAR_END', '2050'))
    
    # --- Roles y permisos por defecto ---
    ROLES = {
        'administrador': 1,
        'investigador': 2,
        'gestor': 3,
        'consultor': 4
    }
    
    @classmethod
    def get_database_url(cls) -> str:
        """Retorna URL de conexión SQLAlchemy"""
        return (
            f"postgresql+psycopg2://{cls.DB_USER}:{cls.DB_PASSWORD}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        )
    
    @classmethod
    def ensure_directories(cls):
        """Asegura que existan los directorios necesarios"""
        for dir_path in [cls.DATA_DIR, cls.OUTPUTS_DIR, cls.TEMP_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directorio verificado: {dir_path}")


# --- Gestión de Conexión a Base de Datos ---
class DatabaseConnection:
    """Gestor de conexiones a PostgreSQL/PostGIS"""
    
    _engine: Optional[Engine] = None
    _session_factory: Optional[sessionmaker] = None
    
    @classmethod
    def get_engine(cls) -> Engine:
        """Obtiene o crea el motor SQLAlchemy"""
        if cls._engine is None:
            try:
                cls._engine = create_engine(
                    Config.get_database_url(),
                    pool_pre_ping=True,
                    pool_size=10,
                    max_overflow=20,
                    echo=Config.DEBUG
                )
                logger.info("Motor de base de datos inicializado")
            except Exception as e:
                logger.error(f"Error al crear motor de BD: {e}")
                raise
        return cls._engine
    
    @classmethod
    def get_session(cls) -> Session:
        """Obtiene una nueva sesión de base de datos"""
        if cls._session_factory is None:
            cls._session_factory = sessionmaker(
                bind=cls.get_engine(),
                autocommit=False,
                autoflush=False
            )
        return cls._session_factory()
    
    @classmethod
    def test_connection(cls) -> bool:
        """Prueba la conexión a la base de datos"""
        try:
            engine = cls.get_engine()
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
                
                # Verificar PostGIS
                result = conn.execute(text("SELECT PostGIS_version()"))
                version = result.fetchone()[0]
                logger.info(f"Conexión exitosa. PostGIS versión: {version}")
            return True
        except Exception as e:
            logger.error(f"Error de conexión: {e}")
            return False
    
    @classmethod
    def execute_query(cls, query: str, params: Dict[str, Any] = None) -> list:
        """Ejecuta una consulta SQL y retorna resultados como lista de diccionarios"""
        engine = cls.get_engine()
        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
    
    @classmethod
    def execute_non_query(cls, query: str, params: Dict[str, Any] = None) -> int:
        """Ejecuta consulta de escritura"""
        engine = cls.get_engine()
        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            conn.commit()
            return result.rowcount
    
    @classmethod
    def read_geodataframe(cls, query: str, geom_col: str = 'geometria', 
                          crs: str = None, params: Dict[str, Any] = None) -> gpd.GeoDataFrame:
        """Lee datos espaciales como GeoDataFrame"""
        import re
        from shapely import wkb
        
        engine = cls.get_engine()
        
        # Caso simple sin parámetros: usar read_postgis directamente
        if not params:
            return gpd.read_postgis(
                sql=text(query),
                con=engine,
                geom_col=geom_col,
                crs=crs or Config.DEFAULT_CRS
            )
        
        # Con parámetros: estrategia robusta usando ST_AsEWKB + pandas.read_sql
        with engine.connect() as conn:
            # Buscar patrón: "columna_original as alias_geom" en la consulta
            # Ejemplo: "ubicacion as geometria"
            patron = re.compile(r'(\w+)\s+as\s+' + re.escape(geom_col), re.IGNORECASE)
            match = patron.search(query)
            
            if match:
                col_original = match.group(1)
                # Reemplazar para obtener geometría como WKB binario
                query_wkb = query.replace(
                    f"{col_original} as {geom_col}",
                    f"ST_AsEWKB({col_original}) as {geom_col}_wkb"
                )
                
                # Usar pandas.read_sql que maneja params correctamente
                df = pd.read_sql(text(query_wkb), conn, params=params)
                
                wkb_col = f"{geom_col}_wkb"
                if wkb_col in df.columns:
                    # Decodificar WKB a objetos Shapely
                    geometrias = []
                    for g in df[wkb_col]:
                        if g is not None:
                            try:
                                geometrias.append(wkb.loads(bytes(g)))
                            except Exception:
                                geometrias.append(None)
                        else:
                            geometrias.append(None)
                    
                    df = df.drop(columns=[wkb_col])
                    return gpd.GeoDataFrame(df, geometry=geometrias, crs=crs or Config.DEFAULT_CRS)
            
            # Fallback: si no encontramos el patrón, intentar read_postgis con bindparams
            try:
                return gpd.read_postgis(
                    sql=text(query).bindparams(**params),
                    con=engine,
                    geom_col=geom_col,
                    crs=crs or Config.DEFAULT_CRS
                )
            except Exception:
                # Último recurso: interpolar params de forma segura para read_postgis
                # (solo para tipos de datos simples: números, strings, fechas)
                query_interpolada = query
                for key, value in params.items():
                    if isinstance(value, str):
                        valor_escapado = value.replace("'", "''")
                        valor_sql = f"'{valor_escapado}'"
                    elif value is None:
                        valor_sql = 'NULL'
                    else:
                        valor_sql = str(value)
                    query_interpolada = query_interpolada.replace(f":{key}", valor_sql)
                
                return gpd.read_postgis(
                    sql=text(query_interpolada),
                    con=engine,
                    geom_col=geom_col,
                    crs=crs or Config.DEFAULT_CRS
                )


# Inicializar al importar
Config.ensure_directories()
