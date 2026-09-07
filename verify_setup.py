"""
Script de Verificación del Entorno
Gemelo Digital de Corredores de Migración

Verifica que todas las dependencias estén instaladas correctamente
y que la conexión a la base de datos funcione.
"""

import sys
import importlib
from pathlib import Path

# Agregar directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


def verificar_dependencias():
    """Verifica que las dependencias principales estén instaladas"""
    print("=" * 60)
    print("VERIFICACIÓN DE DEPENDENCIAS")
    print("=" * 60)
    
    paquetes = [
        ('streamlit', 'Interfaz web'),
        ('pandas', 'Análisis de datos'),
        ('numpy', 'Cálculo numérico'),
        ('geopandas', 'Datos geoespaciales'),
        ('rasterio', 'Datos raster'),
        ('shapely', 'Geometrías'),
        ('fiona', 'Lectura/escritura GIS'),
        ('psycopg2', 'PostgreSQL'),
        ('sqlalchemy', 'ORM SQL'),
        ('geoalchemy2', 'PostGIS en SQLAlchemy'),
        ('scikit-learn', 'Machine Learning'),
        ('networkx', 'Grafos'),
        ('folium', 'Mapas interactivos'),
        ('plotly', 'Gráficos interactivos'),
        ('matplotlib', 'Gráficos estáticos'),
        ('seaborn', 'Visualización estadística'),
        ('reportlab', 'Generación PDF'),
        ('docx', 'Generación Word'),
        ('openpyxl', 'Generación Excel'),
        ('dotenv', 'Variables de entorno'),
        ('bcrypt', 'Hash de contraseñas'),
        ('pyjwt', 'Tokens JWT'),
    ]
    
    # Verificar PyTorch opcionalmente
    try:
        import torch
        print(f"  ✅ torch (PyTorch) - Aprendizaje profundo: v{torch.__version__}")
    except ImportError:
        print(f"  ⚠️  torch (PyTorch) - No instalado (se usará método alternativo)")
    
    todos_ok = True
    
    for paquete, descripcion in paquetes:
        try:
            modulo = importlib.import_module(paquete)
            version = getattr(modulo, '__version__', 'desconocida')
            print(f"  ✅ {paquete} - {descripcion}: v{version}")
        except ImportError as e:
            print(f"  ❌ {paquete} - {descripcion}: NO INSTALADO ({e})")
            todos_ok = False
    
    print()
    return todos_ok


def verificar_base_datos():
    """Verifica conexión a PostgreSQL + PostGIS"""
    print("=" * 60)
    print("VERIFICACIÓN DE BASE DE DATOS")
    print("=" * 60)
    
    try:
        from config import DatabaseConnection
        
        if DatabaseConnection.test_connection():
            print("  ✅ Conexión exitosa a PostgreSQL + PostGIS")
            return True
        else:
            print("  ❌ No se pudo conectar a la base de datos")
            print("     Verifique que PostgreSQL esté corriendo y el archivo .env esté configurado")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def verificar_estructura():
    """Verifica que existan los directorios y archivos necesarios"""
    print("=" * 60)
    print("VERIFICACIÓN DE ESTRUCTURA DE ARCHIVOS")
    print("=" * 60)
    
    archivos_requeridos = [
        'app.py',
        'config.py',
        'requirements.txt',
        '.env.example',
        'README.md',
        'database/schema.sql',
        'database/init_db.py',
        'modules/__init__.py',
        'modules/auth.py',
        'modules/data_ingestion.py',
        'modules/habitat_suitability.py',
        'modules/circuit_theory.py',
        'modules/deep_learning.py',
        'modules/scenario_simulator.py',
        'modules/visualization.py',
        'modules/reports.py',
    ]
    
    todos_ok = True
    
    for archivo in archivos_requeridos:
        ruta = BASE_DIR / archivo
        if ruta.exists():
            print(f"  ✅ {archivo}")
        else:
            print(f"  ❌ {archivo} - FALTANTE")
            todos_ok = False
    
    # Verificar directorios
    for directorio in ['data', 'outputs', 'temp']:
        ruta = BASE_DIR / directorio
        if not ruta.exists():
            ruta.mkdir(parents=True, exist_ok=True)
            print(f"  ℹ️  {directorio}/ - Creado")
        else:
            print(f"  ✅ {directorio}/")
    
    print()
    return todos_ok


def main():
    """Función principal de verificación"""
    print("\n" + "=" * 60)
    print("  GEMELO DIGITAL - VERIFICACIÓN DEL ENTORNO")
    print("=" * 60 + "\n")
    
    resultados = {}
    
    resultados['dependencias'] = verificar_dependencias()
    resultados['estructura'] = verificar_estructura()
    resultados['base_datos'] = verificar_base_datos()
    
    print("=" * 60)
    print("RESUMEN")
    print("=" * 60)
    
    for componente, ok in resultados.items():
        estado = "✅ OK" if ok else "❌ CON ERRORES"
        print(f"  {componente}: {estado}")
    
    print()
    
    if all(resultados.values()):
        print("🎉 ¡Todo está listo! Puede iniciar la aplicación con:")
        print("   streamlit run app.py")
    else:
        print("⚠️  Hay componentes que requieren atención.")
        print("   Corrija los errores antes de iniciar la aplicación.")
        print()
        if not resultados['dependencias']:
            print("   💡 Instalar dependencias faltantes: pip install -r requirements.txt")
        if not resultados['base_datos']:
            print("   💡 Inicializar base de datos: python database/init_db.py")
    
    print()


if __name__ == '__main__':
    main()
