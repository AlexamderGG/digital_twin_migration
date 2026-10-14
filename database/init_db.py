"""
Script de Inicialización de Base de Datos
Gemelo Digital de Corredores de Migración
"""

import os
import sys
import logging
from pathlib import Path

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import bcrypt

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv no instalado. Usando variables de entorno del sistema.")

# --- Configuración ---
# Leemos la URL completa de Neon si estamos en Render
DATABASE_URL = os.getenv('DATABASE_URL')

# Respaldo para entorno local
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'digital_twin_migration')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '1234')

ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@digitaltwin.local')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'Admin123!')
ADMIN_NAME = os.getenv('ADMIN_NAME', 'Administrador del Sistema')

SCHEMA_PATH = Path(__file__).parent / 'schema.sql'

def get_connection():
    """Retorna la conexión a la base de datos dependiendo del entorno"""
    if DATABASE_URL:
        # Conexión para Neon / Render (Requiere SSL)
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    else:
        # Conexión local
        return psycopg2.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER, 
            password=DB_PASSWORD, dbname=DB_NAME
        )

def execute_schema():
    """Ejecuta el archivo schema.sql"""
    logger.info("Ejecutando esquema de base de datos...")
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        cur.execute(sql_content)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Esquema ejecutado exitosamente.")
    except Exception as e:
        logger.error(f"Error al ejecutar esquema: {e}")
        sys.exit(1)

def create_admin_user():
    """Crea el usuario administrador por defecto"""
    logger.info("Creando usuario administrador...")
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        password_hash = bcrypt.hashpw(
            ADMIN_PASSWORD.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        cur.execute("""
            INSERT INTO usuarios 
            (username, email, nombre_completo, password_hash, id_rol, institucion, activo)
            VALUES (%s, %s, %s, %s, 1, %s, TRUE)
            ON CONFLICT (username) DO UPDATE SET
                email = EXCLUDED.email,
                nombre_completo = EXCLUDED.nombre_completo,
                password_hash = EXCLUDED.password_hash,
                id_rol = 1,
                activo = TRUE
            RETURNING id_usuario
        """, (
            ADMIN_USER, ADMIN_EMAIL, ADMIN_NAME, 
            password_hash, 'Institución Central'
        ))
        
        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Usuario administrador creado exitosamente. (ID: {user_id})")
    except Exception as e:
        logger.error(f"Error al crear usuario administrador: {e}")

def insert_sample_data():
    """Inserta datos de ejemplo para pruebas"""
    logger.info("Insertando datos de ejemplo...")
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        especies_ejemplo = [
            (
                'Panthera onca', 'Jaguar', 'Mammalia', 'Carnivora', 'Felidae', 'Panthera',
                'NT', ['Bosque tropical húmedo', 'Sabana', 'Matorral'],
                'Carnívoro',
                '{"temp_min": 15, "temp_max": 35, "precip_min": 800, "precip_max": 4000}'
            )
            # Puedes dejar aquí el resto de tus especies...
        ]
        
        for esp in especies_ejemplo:
            cur.execute("""
                INSERT INTO especies 
                (nombre_cientifico, nombre_comun, clase, orden, familia, genero,
                 categoria_uicn, habitat_pref, dieta, requerimientos_climaticos)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::JSONB)
                ON CONFLICT (nombre_cientifico) DO NOTHING
            """, esp)
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Datos de ejemplo insertados exitosamente.")
    except Exception as e:
        logger.error(f"Error al insertar datos de ejemplo: {e}")

def main():
    """Función principal"""
    logger.info("INICIALIZANDO BASE DE DATOS...")
    
    # Hemos eliminado la función create_database() y el input() para que funcione en Neon y Render
    execute_schema()
    create_admin_user()
    insert_sample_data()
    
    logger.info("¡BASE DE DATOS LISTA!")

if __name__ == '__main__':
    main()