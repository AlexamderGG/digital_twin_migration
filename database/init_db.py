"""
Script de Inicialización de Base de Datos
Gemelo Digital de Corredores de Migración

Este script:
1. Crea la base de datos si no existe
2. Ejecuta el esquema SQL
3. Crea el usuario administrador por defecto
4. Inserta datos de catálogo iniciales
"""

import os
import sys
import logging
from pathlib import Path

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import bcrypt

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv no instalado. Usando variables de entorno del sistema.")

# --- Configuración ---
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'digital_twin_migration')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '1234')

ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@digitaltwin.local')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'Admin123!')
ADMIN_NAME = os.getenv('ADMIN_NAME', 'Administrador del Sistema')

# Ruta al esquema SQL
SCHEMA_PATH = Path(__file__).parent / 'schema.sql'


def create_database():
    """Crea la base de datos si no existe"""
    logger.info("Conectando a PostgreSQL para verificar base de datos...")
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Verificar si la base de datos existe
        cur.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (DB_NAME,))
        exists = cur.fetchone()
        
        if not exists:
            logger.info(f"Creando base de datos '{DB_NAME}'...")
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
            logger.info(f"Base de datos '{DB_NAME}' creada exitosamente.")
        else:
            logger.info(f"Base de datos '{DB_NAME}' ya existe.")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error al crear base de datos: {e}")
        sys.exit(1)


def execute_schema():
    """Ejecuta el archivo schema.sql"""
    logger.info("Ejecutando esquema de base de datos...")
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME
        )
        cur = conn.cursor()
        
        # Leer archivo SQL
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
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME
        )
        cur = conn.cursor()
        
        # Hash de contraseña
        password_hash = bcrypt.hashpw(
            ADMIN_PASSWORD.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        # Insertar usuario administrador (id_rol = 1 = administrador)
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
            ADMIN_USER,
            ADMIN_EMAIL,
            ADMIN_NAME,
            password_hash,
            'Institución Central'
        ))
        
        user_id = cur.fetchone()[0]
        conn.commit()
        
        cur.close()
        conn.close()
        
        logger.info(f"Usuario administrador creado (ID: {user_id})")
        logger.info(f"  Usuario: {ADMIN_USER}")
        logger.info(f"  Email: {ADMIN_EMAIL}")
        logger.info(f"  Contraseña: {ADMIN_PASSWORD}")
        
    except Exception as e:
        logger.error(f"Error al crear usuario administrador: {e}")
        sys.exit(1)


def insert_sample_data():
    """Inserta datos de ejemplo para pruebas"""
    logger.info("Insertando datos de ejemplo...")
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME
        )
        cur = conn.cursor()
        
        # Especies de ejemplo (especies migratorias de América Latina)
        especies_ejemplo = [
            (
                'Panthera onca', 'Jaguar', 'Mammalia', 'Carnivora', 'Felidae', 'Panthera',
                'NT', ['Bosque tropical húmedo', 'Sabana', 'Matorral'],
                'Carnívoro',
                '{"temp_min": 15, "temp_max": 35, "precip_min": 800, "precip_max": 4000}'
            ),
            (
                'Ara macao', 'Guacamayo rojo', 'Aves', 'Psittaciformes', 'Psittacidae', 'Ara',
                'LC', ['Bosque tropical húmedo', 'Várzea'],
                'Frugívoro',
                '{"temp_min": 20, "temp_max": 38, "precip_min": 1000, "precip_max": 5000}'
            ),
            (
                'Chelonia mydas', 'Tortuga verde', 'Reptilia', 'Testudines', 'Cheloniidae', 'Chelonia',
                'EN', ['Océanos tropicales', 'Playas de anidación', 'Pastos marinos'],
                'Herbívoro',
                '{"temp_min": 20, "temp_max": 30, "salinidad_min": 30, "salinidad_max": 38}'
            ),
            (
                'Setophaga striata', 'Reinita rayada', 'Aves', 'Passeriformes', 'Parulidae', 'Setophaga',
                'LC', ['Bosques boreales', 'Manglares', 'Bosques tropicales'],
                'Insectívoro',
                '{"temp_min": -10, "temp_max": 35, "precip_min": 500, "precip_max": 3000}'
            )
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
    logger.info("=" * 60)
    logger.info("INICIALIZACIÓN DE BASE DE DATOS - GEMELO DIGITAL")
    logger.info("=" * 60)
    
    print("\n" + "="*60)
    print("CONFIGURACIÓN ACTUAL:")
    print(f"  Host: {DB_HOST}")
    print(f"  Puerto: {DB_PORT}")
    print(f"  Base de datos: {DB_NAME}")
    print(f"  Usuario: {DB_USER}")
    print("="*60 + "\n")
    
    respuesta = input("¿Desea continuar con la inicialización? (s/n): ")
    if respuesta.lower() not in ('s', 'si', 'y', 'yes'):
        logger.info("Inicialización cancelada por el usuario.")
        sys.exit(0)
    
    create_database()
    execute_schema()
    create_admin_user()
    insert_sample_data()
    
    logger.info("=" * 60)
    logger.info("INICIALIZACIÓN COMPLETADA EXITOSAMENTE")
    logger.info("=" * 60)
    print("\n" + "="*60)
    print("¡BASE DE DATOS LISTA!")
    print(f"Puede iniciar sesión con:")
    print(f"  Usuario: {ADMIN_USER}")
    print(f"  Contraseña: {ADMIN_PASSWORD}")
    print("="*60)


if __name__ == '__main__':
    main()
