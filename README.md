# 🌿 Gemelo Digital de Corredores de Migración de Especies

## Optimización Dinámica de la Conectividad Funcional bajo Cambio Climático

---

## 📋 Descripción

Aplicación web desarrollada en **Python + Streamlit** que implementa un **gemelo digital de paisaje** para modelar el movimiento de especies y optimizar redes de corredores ecológicos de forma adaptativa bajo escenarios de cambio climático.

### 🎯 Características Principales

- **🔐 Gestión de Usuarios**: Módulo completo con roles (Administrador, Investigador, Gestor, Consultor) y permisos granulares
- **📥 Integración de Datos**: Soporte para GBIF, WorldClim/CMIP6, Sentinel/Landsat, telemetría GPS y ciencia ciudadana
- **🧬 Modelos de Hábitat**: Random Forest, Regresión Logística, MaxEnt-like con evaluación AUC/TSS
- **⚡ Teoría de Circuitos**: Cálculo de conectividad funcional (PC, IIC, EC) y corriente de movimiento
- **🧠 Aprendizaje Profundo**: Redes ST-ConvLSTM para predicción espaciotemporal
- **🌍 Simulación de Escenarios**: SSP1-2.6, SSP2-4.5, SSP5-8.5 hasta 2050
- **📊 Visualización**: Mapas interactivos (Folium) y gráficos dinámicos (Plotly)
- **📄 Reportes**: Generación automática en **PDF, Word y Excel**
- **🗄️ Base de Datos**: PostgreSQL + PostGIS para datos espaciales

---

## 🏗️ Arquitectura del Sistema

```
digital_twin_migration/
├── 📄 app.py                      # Aplicación principal Streamlit
├── ⚙️ config.py                   # Configuración y conexión BD
├── 📋 requirements.txt            # Dependencias Python
├── 🔐 .env.example                # Variables de entorno (plantilla)
├── 📖 README.md                   # Este archivo
├── 📁 database/
│   ├── schema.sql                # Esquema PostgreSQL + PostGIS
│   └── init_db.py                # Script de inicialización
└── 📁 modules/
    ├── auth.py                   # Autenticación y roles
    ├── data_ingestion.py         # Carga y gestión de datos
    ├── habitat_suitability.py    # Modelos de idoneidad
    ├── circuit_theory.py         # Teoría de circuitos
    ├── deep_learning.py          # ST-ConvLSTM y predicción
    ├── scenario_simulator.py     # Simulación SSP y optimización
    ├── visualization.py          # Mapas y gráficos
    └── reports.py                # Generación PDF/Word/Excel
```

---

## 🚀 Guía de Despliegue Local en Windows (PowerShell)

### 📋 Requisitos Previos

| Componente | Versión Mínima | Descarga |
|-----------|---------------|----------|
| Python | 3.10+ | https://www.python.org/downloads/ |
| PostgreSQL | 14+ | https://www.postgresql.org/download/windows/ |
| PostGIS | 3.2+ | Incluido en el instalador de PostgreSQL |
| Git (opcional) | Cualquiera | https://git-scm.com/download/win |

---

### 📝 Paso 1: Instalar PostgreSQL + PostGIS

1. Descargue PostgreSQL desde: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
2. Ejecute el instalador como **Administrador**
3. Durante la instalación:
   - Establezca una contraseña para el usuario `postgres` (recuérdela)
   - Puerto: `5432` (predeterminado)
   - **IMPORTANTE**: En la pantalla "Stack Builder", seleccione **PostGIS** para instalar
4. Finalice la instalación y verifique que PostgreSQL esté corriendo:
   ```powershell
   # Verificar servicio
   Get-Service -Name postgresql*
   ```

---

### 📝 Paso 2: Preparar el Entorno Python

Abra **PowerShell** como usuario normal y ejecute:

```powershell
# 1. Verificar Python
python --version
# Debe mostrar Python 3.10.x o superior

# 2. Actualizar pip
python -m pip install --upgrade pip

# 3. Instalar virtualenv (recomendado)
pip install virtualenv
```

---

### 📝 Paso 3: Descargar y Preparar el Proyecto

```powershell
# 1. Crear carpeta del proyecto (ajuste la ruta según prefiera)
mkdir C:\Proyectos\digital_twin_migration
cd C:\Proyectos\digital_twin_migration

# 2. Copiar aquí todos los archivos del proyecto

# 3. Crear entorno virtual
python -m venv venv

# 4. Activar el entorno virtual
.\venv\Scripts\Activate.ps1

# NOTA: Si recibe error de política de ejecución, ejecute primero:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### 📝 Paso 4: Instalar Dependencias

Con el entorno virtual activado:

```powershell
# Instalar todas las dependencias
pip install -r requirements.txt

# ⚠️ Si hay errores con paquetes geoespaciales (GDAL, rasterio, fiona):
# Descargue los wheels precompilados desde https://www.lfd.uci.edu/~gohlke/pythonlibs/
# E instale manualmente, por ejemplo:
# pip install .\GDAL-3.8.4-cp312-cp312-win_amd64.whl
# pip install .\rasterio-1.3.9-cp312-cp312-win_amd64.whl
# pip install .\Fiona-1.9.6-cp312-cp312-win_amd64.whl
```

---

### 📝 Paso 5: Configurar Variables de Entorno

```powershell
# Copiar archivo de configuración
Copy-Item .env.example .env

# Editar el archivo .env con sus datos
# Puede usar Notepad:
notepad .env
```

**Edite estos valores en `.env`:**
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=digital_twin_migration
DB_USER=postgres
DB_PASSWORD=SU_CONTRASEÑA_DE_POSTGRES_AQUI

SECRET_KEY=una_clave_larga_y_aleatoria_aqui_cambiar_en_produccion
```

---

### 📝 Paso 6: Inicializar la Base de Datos

```powershell
# Asegúrese de estar en el directorio del proyecto con venv activado

# Ejecutar script de inicialización
python database\init_db.py
```

**El script le preguntará si desea continuar. Presione `s` y Enter.**

✅ **Resultado esperado:**
- Base de datos `digital_twin_migration` creada
- Extensiones PostGIS habilitadas
- Tablas y catálogos creados
- Usuario administrador creado:
  - **Usuario:** `admin`
  - **Contraseña:** `Admin123!`
- Datos de ejemplo (4 especies) insertados

---

### 📝 Paso 7: Iniciar la Aplicación Streamlit

```powershell
# Ejecutar la aplicación
streamlit run app.py
```

✅ **La aplicación se abrirá automáticamente en su navegador** (normalmente en `http://localhost:8501`)

---

### 📝 Paso 8: Primer Inicio de Sesión

1. En la pantalla de login, ingrese:
   - **Usuario:** `admin`
   - **Contraseña:** `Admin123!`

2. **IMPORTANTE**: Cambie la contraseña por defecto en la sección **👥 Gestión Usuarios → Cambiar Contraseña**

3. Pruebe la conexión a la base de datos haciendo clic en **"Probar Conexión BD"**

---

## 🎮 Guía Rápida de Uso

### Flujo de Trabajo Recomendado

1. **📥 Cargar Datos** → Suba registros de presencia de especies
2. **🧬 Modelar Hábitat** → Entrene modelo de idoneidad para la especie
3. **⚡ Analizar Conectividad** → Evalúe la red actual
4. **🌍 Simular Escenarios** → Compare diseño estático vs dinámico
5. **📄 Generar Reportes** → Exporte resultados en PDF/Word/Excel

### Roles de Usuario

| Rol | Permisos |
|-----|----------|
| 👑 **Administrador** | Acceso completo, gestión de usuarios |
| 🔬 **Investigador** | Ejecutar modelos, simular escenarios, generar reportes |
| 📊 **Gestor** | Cargar datos, generar reportes |
| 👁️ **Consultor** | Solo visualización de resultados |

---

## 🔧 Solución de Problemas Comunes

### ❌ Error: "No se puede cargar el archivo venv\Scripts\Activate.ps1"
```powershell
# Solución: Permitir ejecución de scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Presione 'S' para confirmar
```

### ❌ Error de conexión a PostgreSQL
1. Verifique que el servicio esté corriendo:
   ```powershell
   Get-Service postgresql* | Start-Service
   ```
2. Verifique credenciales en `.env`
3. Asegúrese de que PostGIS esté instalado

### ❌ Error instalando paquetes geoespaciales
```powershell
# Opción 1: Usar ruedas precompiladas
# Descargar de https://www.lfd.uci.edu/~gohlke/pythonlibs/
# Instalar en orden: GDAL → Fiona → Rasterio → GeoPandas

# Opción 2: Usar conda (si tiene Anaconda/Miniconda)
conda install -c conda-forge geopandas rasterio fiona
```

### ❌ La aplicación no abre en el navegador
- Acceda manualmente a: `http://localhost:8501`
- Verifique que no haya otro proceso usando el puerto 8501
- Use otro puerto: `streamlit run app.py --server.port 8502`

---

## 📊 Estructura de la Base de Datos

### Tablas Principales

| Tabla | Propósito |
|-------|-----------|
| `usuarios` / `roles` | Gestión de accesos |
| `especies` | Catálogo taxonómico y ecológico |
| `registros_presencia` | Observaciones de especies (GBIF, etc.) |
| `telemetria` | Datos GPS de movimiento |
| `uso_suelo` | Capas de cobertura terrestre |
| `capa_resistencia` | Resistencia del paisaje al movimiento |
| `modelos_habitat` | Modelos de idoneidad entrenados |
| `simulaciones` | Ejecuciones de escenarios |
| `resultados_conectividad` | Métricas por año y simulación |
| `corredores` | Redes de corredores resultantes |
| `parches_nucleo` | Parches de hábitat prioritarios |
| `reportes` | Historial de reportes generados |

---

## 🧪 Prueba Rápida del Sistema

Para verificar que todo funciona correctamente:

1. Inicie sesión como `admin`
2. Vaya a **🌍 Simulación de Escenarios**
3. Seleccione una especie y escenario SSP
4. Haga clic en **"Ejecutar Simulación Comparativa"**
5. La simulación generará datos sintéticos realistas y mostrará:
   - Gráficos de evolución de conectividad
   - Comparación estático vs dinámico
   - Mapa de corredores ecológicos
6. Vaya a **📄 Reportes** y genere los tres formatos

---

## 📚 Referencias Metodológicas

1. **McRae, B. H. et al. (2008)** - Using circuit theory to model connectivity in ecology, evolution, and conservation
2. **Saura, S. & Pascual-Hortal, L. (2007)** - A new habitat availability index to integrate connectivity in landscape conservation planning
3. **IPCC AR6** - Shared Socioeconomic Pathways (SSP) scenarios
4. **Phillips, S. J. et al. (2006)** - Maximum entropy modeling of species geographic distributions
5. **Shi, X. et al. (2015)** - Deep learning for precipitation nowcasting: A benchmark and a new model

---

## 👥 Equipo y Soporte

Para soporte técnico o consultas sobre la implementación:
- Verifique primero la sección **Solución de Problemas**
- Revise los logs en la consola de PowerShell
- Consulte la documentación de cada módulo en los comentarios del código

---

## 📄 Licencia

Este software se desarrolla como herramienta de apoyo a la investigación y planificación en conservación biológica.

---

<div align="center">

**🌿 Gemelo Digital de Corredores de Migración**  
*Optimización Dinámica de la Conectividad Funcional bajo Cambio Climático*

Versión 1.0.0

</div>
