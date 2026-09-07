-- =============================================================================
-- GEMELO DIGITAL DE CORREDORES DE MIGRACIÓN DE ESPECIES
-- Esquema de Base de Datos PostgreSQL + PostGIS
-- =============================================================================

-- Habilitar extensiones necesarias
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- MÓDULO 1: GESTIÓN DE USUARIOS Y ROLES
-- =============================================================================

-- Tabla de roles
CREATE TABLE IF NOT EXISTS roles (
    id_rol SERIAL PRIMARY KEY,
    nombre_rol VARCHAR(50) UNIQUE NOT NULL,
    descripcion TEXT,
    permisos JSONB DEFAULT '{}'::JSONB,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE
);

-- Roles predefinidos
INSERT INTO roles (nombre_rol, descripcion, permisos) VALUES
('administrador', 'Acceso completo al sistema', 
 '{"usuarios": {"crear": true, "editar": true, "eliminar": true, "ver": true},
   "datos": {"cargar": true, "editar": true, "eliminar": true, "ver": true},
   "modelos": {"ejecutar": true, "configurar": true, "ver": true},
   "escenarios": {"crear": true, "ejecutar": true, "eliminar": true, "ver": true},
   "reportes": {"generar": true, "exportar": true, "ver": true}}'::JSONB),
('investigador', 'Ejecuta modelos y analiza resultados',
 '{"usuarios": {"ver": true},
   "datos": {"cargar": true, "editar": true, "ver": true},
   "modelos": {"ejecutar": true, "configurar": true, "ver": true},
   "escenarios": {"crear": true, "ejecutar": true, "ver": true},
   "reportes": {"generar": true, "exportar": true, "ver": true}}'::JSONB),
('gestor', 'Gestiona datos y genera reportes',
 '{"usuarios": {"ver": true},
   "datos": {"cargar": true, "editar": true, "ver": true},
   "modelos": {"ver": true},
   "escenarios": {"ver": true},
   "reportes": {"generar": true, "exportar": true, "ver": true}}'::JSONB),
('consultor', 'Solo visualización de resultados',
 '{"usuarios": {"ver": false},
   "datos": {"ver": true},
   "modelos": {"ver": true},
   "escenarios": {"ver": true},
   "reportes": {"ver": true, "exportar": true}}'::JSONB)
ON CONFLICT (nombre_rol) DO NOTHING;

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    nombre_completo VARCHAR(150) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    id_rol INTEGER REFERENCES roles(id_rol) DEFAULT 4,
    institucion VARCHAR(150),
    telefono VARCHAR(30),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE,
    token_reset VARCHAR(255),
    expiracion_token TIMESTAMP
);

-- Tabla de sesiones
CREATE TABLE IF NOT EXISTS sesiones (
    id_sesion UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    id_usuario INTEGER REFERENCES usuarios(id_usuario),
    token_jwt TEXT,
    fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_expiracion TIMESTAMP,
    ip_cliente VARCHAR(50),
    activa BOOLEAN DEFAULT TRUE
);

-- =============================================================================
-- MÓDULO 2: CATÁLOGOS Y REFERENCIA
-- =============================================================================

-- Catálogo de especies
CREATE TABLE IF NOT EXISTS especies (
    id_especie SERIAL PRIMARY KEY,
    nombre_cientifico VARCHAR(150) UNIQUE NOT NULL,
    nombre_comun VARCHAR(150),
    reino VARCHAR(50) DEFAULT 'Animalia',
    filo VARCHAR(100),
    clase VARCHAR(100),
    orden VARCHAR(100),
    familia VARCHAR(100),
    genero VARCHAR(100),
    categoria_uicn VARCHAR(5),
    habitat_pref TEXT[],
    dieta VARCHAR(100),
    rango_distribucion GEOMETRY(MultiPolygon, 4326),
    requerimientos_climaticos JSONB DEFAULT '{}'::JSONB,
    descripcion TEXT,
    fuente VARCHAR(100) DEFAULT 'GBIF',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_especies_nombre ON especies(nombre_cientifico);
CREATE INDEX idx_especies_geom ON especies USING GIST(rango_distribucion);

-- Catálogo de escenarios climáticos SSP
CREATE TABLE IF NOT EXISTS escenarios_climaticos (
    id_escenario SERIAL PRIMARY KEY,
    codigo_ssp VARCHAR(20) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    modelo_cmip6 VARCHAR(100),
    año_inicio INTEGER DEFAULT 2020,
    año_fin INTEGER DEFAULT 2100,
    parametros JSONB DEFAULT '{}'::JSONB
);

INSERT INTO escenarios_climaticos (codigo_ssp, nombre, descripcion, modelo_cmip6) VALUES
('SSP1-2.6', 'Sostenibilidad', 'Camino sostenible con mitigación fuerte del cambio climático', 'MRI-ESM2-0'),
('SSP2-4.5', 'Intermedio', 'Desarrollo medio con desafíos moderados de mitigación', 'MRI-ESM2-0'),
('SSP5-8.5', 'Fósiles y desarrollo', 'Alto consumo de fósiles y altas emisiones', 'MRI-ESM2-0')
ON CONFLICT (codigo_ssp) DO NOTHING;

-- =============================================================================
-- MÓDULO 3: DATOS ESPACIALES
-- =============================================================================

-- Registros de presencia de especies
CREATE TABLE IF NOT EXISTS registros_presencia (
    id_registro SERIAL PRIMARY KEY,
    id_especie INTEGER REFERENCES especies(id_especie),
    fecha_observacion DATE,
    ubicacion GEOMETRY(Point, 4326) NOT NULL,
    latitud DOUBLE PRECISION,
    longitud DOUBLE PRECISION,
    fuente VARCHAR(100) DEFAULT 'GBIF',
    id_fuente_original VARCHAR(100),
    certeza DOUBLE PRECISION DEFAULT 1.0,
    datos_adicionales JSONB DEFAULT '{}'::JSONB,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validado BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_registros_especie ON registros_presencia(id_especie);
CREATE INDEX idx_registros_geom ON registros_presencia USING GIST(ubicacion);
CREATE INDEX idx_registros_fecha ON registros_presencia(fecha_observacion);

-- Datos de telemetría (trayectorias)
CREATE TABLE IF NOT EXISTS telemetria (
    id_telemetria SERIAL PRIMARY KEY,
    id_especie INTEGER REFERENCES especies(id_especie),
    id_individuo VARCHAR(50),
    fecha_hora TIMESTAMP NOT NULL,
    ubicacion GEOMETRY(Point, 4326) NOT NULL,
    latitud DOUBLE PRECISION,
    longitud DOUBLE PRECISION,
    altitud DOUBLE PRECISION,
    velocidad DOUBLE PRECISION,
    direccion DOUBLE PRECISION,
    precision_gps DOUBLE PRECISION,
    dispositivo VARCHAR(100),
    fuente VARCHAR(100),
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_telemetria_especie ON telemetria(id_especie);
CREATE INDEX idx_telemetria_geom ON telemetria USING GIST(ubicacion);
CREATE INDEX idx_telemetria_individuo ON telemetria(id_individuo);

-- Capa de uso del suelo
CREATE TABLE IF NOT EXISTS uso_suelo (
    id_uso_suelo SERIAL PRIMARY KEY,
    año INTEGER NOT NULL,
    fuente VARCHAR(100) DEFAULT 'Sentinel-2',
    geometria GEOMETRY(MultiPolygon, 4326) NOT NULL,
    clase_uso VARCHAR(100) NOT NULL,
    codigo_clase INTEGER,
    area_km2 DOUBLE PRECISION,
    porcentaje_vegetacion DOUBLE PRECISION,
    datos_adicionales JSONB DEFAULT '{}'::JSONB,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_uso_suelo_año ON uso_suelo(año);
CREATE INDEX idx_uso_suelo_geom ON uso_suelo USING GIST(geometria);

-- Capa de resistencia del paisaje
CREATE TABLE IF NOT EXISTS capa_resistencia (
    id_capa SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    año INTEGER,
    id_escenario INTEGER REFERENCES escenarios_climaticos(id_escenario),
    descripcion TEXT,
    resolucion DOUBLE PRECISION DEFAULT 30, -- metros
    unidad VARCHAR(50) DEFAULT 'metros',
    ruta_raster VARCHAR(500),
    parametros JSONB DEFAULT '{}'::JSONB,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    id_usuario_creador INTEGER REFERENCES usuarios(id_usuario)
);

-- =============================================================================
-- MÓDULO 4: MODELOS Y RESULTADOS
-- =============================================================================

-- Modelos de idoneidad de hábitat
CREATE TABLE IF NOT EXISTS modelos_habitat (
    id_modelo SERIAL PRIMARY KEY,
    id_especie INTEGER REFERENCES especies(id_especie),
    nombre VARCHAR(150) NOT NULL,
    algoritmo VARCHAR(100) DEFAULT 'MaxEnt',
    variables_predictoras TEXT[],
    rendimiento JSONB DEFAULT '{}'::JSONB, -- AUC, TSS, etc.
    ruta_modelo VARCHAR(500),
    ruta_raster_idoneidad VARCHAR(500),
    año_entrenamiento INTEGER,
    parametros JSONB DEFAULT '{}'::JSONB,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    id_usuario INTEGER REFERENCES usuarios(id_usuario)
);

-- Modelos de aprendizaje profundo espaciotemporal
CREATE TABLE IF NOT EXISTS modelos_dl (
    id_modelo_dl SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    arquitectura VARCHAR(100) DEFAULT 'STGCN',
    id_especie INTEGER REFERENCES especies(id_especie),
    variables_entrada TEXT[],
    ruta_modelo VARCHAR(500),
    historial_entrenamiento JSONB DEFAULT '{}'::JSONB,
    metricas JSONB DEFAULT '{}'::JSONB,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    id_usuario INTEGER REFERENCES usuarios(id_usuario)
);

-- =============================================================================
-- MÓDULO 5: ESCENARIOS Y SIMULACIONES
-- =============================================================================

-- Simulaciones ejecutadas
CREATE TABLE IF NOT EXISTS simulaciones (
    id_simulacion SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    descripcion TEXT,
    tipo VARCHAR(50) NOT NULL, -- 'base', 'estatica', 'dinamica'
    id_escenario INTEGER REFERENCES escenarios_climaticos(id_escenario),
    id_especie INTEGER REFERENCES especies(id_especie),
    año_inicio INTEGER DEFAULT 2024,
    año_fin INTEGER DEFAULT 2050,
    parametros JSONB DEFAULT '{}'::JSONB,
    estado VARCHAR(30) DEFAULT 'pendiente', -- pendiente, ejecutando, completada, error
    progreso INTEGER DEFAULT 0,
    fecha_inicio TIMESTAMP,
    fecha_fin TIMESTAMP,
    ruta_resultados VARCHAR(500),
    id_usuario INTEGER REFERENCES usuarios(id_usuario),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Resultados de conectividad por simulación
CREATE TABLE IF NOT EXISTS resultados_conectividad (
    id_resultado SERIAL PRIMARY KEY,
    id_simulacion INTEGER REFERENCES simulaciones(id_simulacion) ON DELETE CASCADE,
    año INTEGER NOT NULL,
    metrica VARCHAR(100) NOT NULL, -- 'PC', 'IIC', 'EC', 'corriente_total', etc.
    valor DOUBLE PRECISION NOT NULL,
    unidad VARCHAR(50),
    descripcion TEXT,
    datos_adicionales JSONB DEFAULT '{}'::JSONB
);

CREATE INDEX idx_resultados_simulacion ON resultados_conectividad(id_simulacion);

-- Corredores ecológicos resultantes
CREATE TABLE IF NOT EXISTS corredores (
    id_corredor SERIAL PRIMARY KEY,
    id_simulacion INTEGER REFERENCES simulaciones(id_simulacion) ON DELETE CASCADE,
    nombre VARCHAR(150),
    tipo VARCHAR(50) DEFAULT 'dinamico', -- 'estatico', 'dinamico'
    año INTEGER,
    geometria GEOMETRY(LineString, 4326) NOT NULL,
    longitud_km DOUBLE PRECISION,
    ancho_promedio DOUBLE PRECISION,
    resistencia_promedio DOUBLE PRECISION,
    importancia DOUBLE PRECISION, -- pagerank o centralidad
    prioridad INTEGER DEFAULT 3, -- 1: alta, 2: media, 3: baja
    datos_adicionales JSONB DEFAULT '{}'::JSONB
);

CREATE INDEX idx_corredores_simulacion ON corredores(id_simulacion);
CREATE INDEX idx_corredores_geom ON corredores USING GIST(geometria);

-- Parches de hábitat núcleo
CREATE TABLE IF NOT EXISTS parches_nucleo (
    id_parche SERIAL PRIMARY KEY,
    id_simulacion INTEGER REFERENCES simulaciones(id_simulacion) ON DELETE CASCADE,
    id_especie INTEGER REFERENCES especies(id_especie),
    año INTEGER,
    geometria GEOMETRY(Polygon, 4326) NOT NULL,
    area_km2 DOUBLE PRECISION,
    calidad_habitat DOUBLE PRECISION,
    importancia_conectividad DOUBLE PRECISION,
    datos_adicionales JSONB DEFAULT '{}'::JSONB
);

CREATE INDEX idx_parches_geom ON parches_nucleo USING GIST(geometria);

-- =============================================================================
-- MÓDULO 6: REPORTES Y AUDITORÍA
-- =============================================================================

-- Reportes generados
CREATE TABLE IF NOT EXISTS reportes (
    id_reporte SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    tipo VARCHAR(20) NOT NULL, -- 'PDF', 'WORD', 'EXCEL'
    id_simulacion INTEGER REFERENCES simulaciones(id_simulacion),
    contenido JSONB DEFAULT '{}'::JSONB,
    ruta_archivo VARCHAR(500),
    fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    id_usuario INTEGER REFERENCES usuarios(id_usuario)
);

-- Tabla de auditoría
CREATE TABLE IF NOT EXISTS auditoria (
    id_auditoria SERIAL PRIMARY KEY,
    id_usuario INTEGER REFERENCES usuarios(id_usuario),
    accion VARCHAR(100) NOT NULL,
    tabla_afectada VARCHAR(100),
    id_registro INTEGER,
    detalles JSONB DEFAULT '{}'::JSONB,
    ip_cliente VARCHAR(50),
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- VISTAS ÚTILES
-- =============================================================================

-- Vista de resumen de especies con conteo de registros
CREATE OR REPLACE VIEW v_resumen_especies AS
SELECT 
    e.id_especie,
    e.nombre_cientifico,
    e.nombre_comun,
    e.categoria_uicn,
    COUNT(r.id_registro) AS total_registros,
    MAX(r.fecha_observacion) AS ultima_observacion,
    e.fecha_creacion
FROM especies e
LEFT JOIN registros_presencia r ON e.id_especie = r.id_especie
GROUP BY e.id_especie, e.nombre_cientifico, e.nombre_comun, e.categoria_uicn;

-- Vista de resumen de simulaciones
CREATE OR REPLACE VIEW v_resumen_simulaciones AS
SELECT 
    s.id_simulacion,
    s.nombre,
    s.tipo,
    ec.codigo_ssp,
    e.nombre_cientifico AS especie,
    s.año_inicio,
    s.año_fin,
    s.estado,
    s.progreso,
    s.fecha_inicio,
    s.fecha_fin,
    u.nombre_completo AS usuario_creador
FROM simulaciones s
LEFT JOIN escenarios_climaticos ec ON s.id_escenario = ec.id_escenario
LEFT JOIN especies e ON s.id_especie = e.id_especie
LEFT JOIN usuarios u ON s.id_usuario = u.id_usuario;

-- =============================================================================
-- FUNCIONES Y TRIGGERS
-- =============================================================================

-- Función para actualizar fecha de último acceso
CREATE OR REPLACE FUNCTION actualizar_ultimo_acceso()
RETURNS TRIGGER AS $$
BEGIN
    NEW.ultimo_acceso = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_actualizar_acceso
    BEFORE UPDATE ON usuarios
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_ultimo_acceso();

-- Función para registrar auditoría automáticamente
CREATE OR REPLACE FUNCTION registrar_auditoria()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO auditoria (accion, tabla_afectada, id_registro, detalles)
    VALUES (TG_OP, TG_TABLE_NAME, OLD.id, row_to_json(OLD));
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- COMENTARIOS Y DOCUMENTACIÓN
-- =============================================================================

COMMENT ON DATABASE digital_twin_migration IS 
'Base de datos del Gemelo Digital de Corredores de Migración de Especies bajo Cambio Climático';

COMMENT ON TABLE especies IS 
'Catálogo de especies con información taxonómica y ecológica';

COMMENT ON TABLE registros_presencia IS 
'Registros de presencia de especies provenientes de GBIF, ciencia ciudadana u otras fuentes';

COMMENT ON TABLE capa_resistencia IS 
'Capas raster de resistencia del paisaje calibradas empíricamente';

COMMENT ON TABLE simulaciones IS 
'Registro de todas las simulaciones de conectividad ejecutadas en el sistema';

COMMENT ON TABLE corredores IS 
'Corredores ecológicos resultantes de las simulaciones de optimización dinámica';
