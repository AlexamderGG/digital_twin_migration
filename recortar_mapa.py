import geopandas as gpd
from shapely.geometry import box

# 1. Rutas de archivo
ruta_archivo_original = "C:/Users/alexp/Downloads/Bosque_NoBosque_Perdida_2001_2025_Vector/Bosque_No_Bosque_2025.shp"
ruta_salida = "C:/Users/alexp/Downloads/Bosque_NoBosque_Perdida_2001_2025_Vector/Bosque_NoBosque_2025_Recortado.shp"

# 2. Tu área de interés en grados (Longitud/Latitud)
lon_min, lat_min, lon_max, lat_max = -76.906362, -12.354394, -71.833690, -2.295275

print("1. Verificando el sistema de coordenadas (CRS) del archivo MINAM...")
# Leer solo la primera fila (para no saturar la RAM) y obtener su CRS
info_shp = gpd.read_file(ruta_archivo_original, rows=1)
crs_original = info_shp.crs
print(f"-> El archivo original está en: {crs_original}")

# 3. Crear una caja con tus coordenadas y transformarla al sistema del archivo
caja_grados = gpd.GeoDataFrame({"geometry": [box(lon_min, lat_min, lon_max, lat_max)]}, crs="EPSG:4326")
caja_proyectada = caja_grados.to_crs(crs_original)

# Extraer los nuevos límites matemáticos para el recorte
bbox_corregido = tuple(caja_proyectada.total_bounds)
print(f"-> Coordenadas convertidas para el recorte: {bbox_corregido}")

print("\n2. Iniciando lectura y recorte espacial...")
# Ahora sí filtramos usando las coordenadas en el mismo "idioma" del archivo
gdf_recortado = gpd.read_file(ruta_archivo_original, bbox=bbox_corregido)

print(f"¡Recorte exitoso! Se encontraron {len(gdf_recortado)} polígonos en esta zona.")

if len(gdf_recortado) > 0:
    print("\n3. Preparando archivo para el Gemelo Digital...")
    # Convertir el mapa de vuelta a grados (EPSG:4326)
    gdf_final = gdf_recortado.to_crs("EPSG:4326")
    
    print("4. Aplicando compresión geométrica (Simplificación)...")
    # tolerance=0.002 equivale a unos 200 metros. 
    # Mantiene la forma general del corredor ecológico, pero borra miles de vértices innecesarios.
    gdf_final['geometry'] = gdf_final.geometry.simplify(tolerance=0.002, preserve_topology=True)
    
    print("5. Limpiando datos tabulares pesados...")
    # Los shapefiles del gobierno traen 20 columnas inútiles que pesan mucho. 
    # Conservamos solo la geometría y la clase. 
    # (Abre la tabla de atributos para confirmar el nombre exacto de la columna del MINAM, suele ser 'bosque', 'descrip' o similar)
    columnas_a_mantener = [col for col in gdf_final.columns if col.lower() in ['geometry', 'bosque', 'descrip', 'cobertura']]
    if len(columnas_a_mantener) > 1: # Si encontró alguna columna de descripción
        gdf_final = gdf_final[columnas_a_mantener]
    
    gdf_final.to_file(ruta_salida)
    print(f"-> ¡Listo! Archivo guardado como: {ruta_salida}")
    print("-> Ahora sí, comprime este nuevo archivo en un .zip. Debería pesar poquísimos megas.")
else:
    print("-> Sigue habiendo 0 polígonos.")