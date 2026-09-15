import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, GeoJSON, Marker, Popup, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import api from '../services/api';

// Icono personalizado para centroides
const createCentroidIcon = (color) => L.divIcon({
  className: 'custom-centroid-marker',
  html: `<div style="background-color: ${color}; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 4px rgba(0,0,0,0.5);"></div>`,
  iconSize: [14, 14],
  iconAnchor: [7, 7]
});

export default function SpeciesMigrationView() {
  const [especies, setEspecies] = useState([]);
  const [selectedEspecie, setSelectedEspecie] = useState('');
  const [deltaTemp, setDeltaTemp] = useState(1.5); // Incremento/decremento en °C
  const [loading, setLoading] = useState(false);
  const [predictionData, setPredictionData] = useState(null);
  const [error, setError] = useState('');

  // 1. Cargar catálogo de especies al montar
  useEffect(() => {
    const fetchEspecies = async () => {
      try {
        const res = await api.get('/datos/especies');
        // Extraemos 'data' desde 'res.data'
        if (res.data.success && res.data.data.length > 0) {
          setEspecies(res.data.data);
          // Convertimos a string por consistencia con el select
          setSelectedEspecie(res.data.data[0].id_especie.toString()); 
        }
      } catch (err) {
        console.error("Error cargando especies:", err);
      }
    };
    fetchEspecies();
  }, []);

  // 2. Ejecutar predicción con el mejor modelo
  const handlePredecir = async () => {
    if (!selectedEspecie) return;
    
    setLoading(true);
    setError('');             // Limpiamos errores previos
    setPredictionData(null);  // Limpiamos resultados previos

    try {
      const response = await api.post('/habitat/predecir-migracion', {
        id_especie: parseInt(selectedEspecie),
        delta_temp: parseFloat(deltaTemp),
        criterio_optimo: 'auc'
      });
      
      // Dependiendo de si tu backend envuelve la respuesta en {data: ...} o no
      const dataToSet = response.data.data ? response.data.data : response.data;
      setPredictionData(dataToSet);

    } catch (err) {
      console.error("Error al predecir migración:", err);
      // Extraemos el mensaje de error del backend (detail)
      const mensajeError = err.response?.data?.detail || err.message || 'Error de conexión con el servidor.';
      setError(mensajeError);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col lg:flex-row h-screen bg-slate-50 text-slate-800">
      {/* Panel de Controles Lateral */}
      <div className="w-full lg:w-96 p-6 bg-white shadow-md z-10 flex flex-col gap-5 overflow-y-auto">
        <div>
          <h2 className="text-xl font-bold text-emerald-800">🌿 Predicción de Migración</h2>
          <p className="text-xs text-slate-500">Gemelo Digital Climático</p>
        </div>

        {/* Selector de Especie */}
        <div>
          <label className="block text-sm font-semibold mb-1">Especie Objetivo:</label>
          <select 
            value={selectedEspecie} 
            onChange={(e) => setSelectedEspecie(e.target.value)}
            className="w-full border rounded-lg p-2 text-sm bg-slate-50 focus:ring-2 focus:ring-emerald-500 outline-none"
          >
            {especies.map(esp => (
              <option key={esp.id_especie} value={esp.id_especie}>
                {esp.nombre_cientifico} ({esp.nombre_comun || 'Sin nombre común'})
              </option>
            ))}
          </select>
        </div>

        {/* Slider de Variación de Temperatura */}
        <div className="bg-slate-100 p-4 rounded-xl">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-semibold">Variación de Temperatura:</span>
            <span className={`text-sm font-extrabold ${deltaTemp >= 0 ? 'text-rose-600' : 'text-blue-600'}`}>
              {deltaTemp > 0 ? `+${deltaTemp}` : deltaTemp} °C
            </span>
          </div>
          <input 
            type="range" 
            min="-2.0" 
            max="4.0" 
            step="0.5" 
            value={deltaTemp}
            onChange={(e) => setDeltaTemp(e.target.value)}
            className="w-full accent-emerald-600 cursor-pointer"
          />
          <div className="flex justify-between text-[11px] text-slate-400 mt-1">
            <span>-2.0°C (Enfriamiento)</span>
            <span>0.0°C</span>
            <span>+4.0°C (Calentamiento)</span>
          </div>
        </div>

        {/* Botón Ejecutar */}
        <button
          onClick={handlePredecir}
          disabled={loading}
          className="w-full py-2.5 bg-emerald-700 hover:bg-emerald-800 text-white font-medium rounded-lg shadow transition disabled:opacity-50"
        >
          {loading ? 'Calculando con el mejor modelo...' : 'Simular Migración'}
        </button>
        {error && (
          <div className="mt-3 bg-rose-50 text-rose-600 p-3 rounded-lg text-sm border border-rose-200">
            <strong>Atención:</strong> {error}
          </div>
        )}
        {/* Tarjeta con Resultados del Mejor Modelo */}
        {predictionData && (
          <div className="flex flex-col gap-3 mt-2 border-t pt-4 text-sm">
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
              <span className="text-xs text-emerald-600 font-bold uppercase tracking-wider block">
                Mejor Modelo Autoseleccionado
              </span>
              <p className="font-semibold text-emerald-900">{predictionData.mejor_modelo.nombre}</p>
              <div className="flex gap-4 mt-1 text-xs text-slate-600">
                <span>AUC: <strong>{predictionData.mejor_modelo.auc.toFixed(3)}</strong></span>
                <span>TSS: <strong>{predictionData.mejor_modelo.tss.toFixed(3)}</strong></span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-center">
              <div className="p-2.5 bg-slate-100 rounded-lg">
                <span className="text-xs text-slate-500 block">Desplazamiento</span>
                <span className="font-bold text-slate-800">{predictionData.metricas.distancia_km} km</span>
              </div>
              <div className="p-2.5 bg-slate-100 rounded-lg">
                <span className="text-xs text-slate-500 block">Cambio Hábitat</span>
                <span className={`font-bold ${predictionData.metricas.cambio_superficie_pct >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {predictionData.metricas.cambio_superficie_pct > 0 ? '+' : ''}{predictionData.metricas.cambio_superficie_pct}%
                </span>
              </div>
            </div>

            {/* Leyenda */}
            <div className="text-xs text-slate-500 space-y-1 mt-2">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-blue-500 inline-block"></span>
                <span>Centroide Actual</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-rose-500 inline-block"></span>
                <span>Centroide Proyectado</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-4 h-0.5 bg-amber-500 inline-block"></span>
                <span>Vector de Desplazamiento</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Mapa Principal */}
      <div className="flex-1 h-full relative">
        <MapContainer 
          center={[-9.19, -75.01]} // Coordenadas de referencia (ej. Perú/Amazonía)
          zoom={6} 
          className="w-full h-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {predictionData && (
            <>
              {/* Capa de Distribución Actual (Azul) */}
              {predictionData.geojson_actual && (
                <GeoJSON 
                  key={`act-${selectedEspecie}`}
                  data={predictionData.geojson_actual} 
                  style={{ color: '#2563eb', weight: 1.5, fillOpacity: 0.25 }}
                />
              )}

              {/* Capa de Distribución Futura (Naranja/Rojo) */}
              {predictionData.geojson_futuro && (
                <GeoJSON 
                  key={`fut-${selectedEspecie}-${deltaTemp}`}
                  data={predictionData.geojson_futuro} 
                  style={{ color: '#dc2626', weight: 1.5, fillOpacity: 0.35 }}
                />
              )}

              {/* Marcador Centroide Actual */}
              <Marker 
                position={[predictionData.centroide_actual.lat, predictionData.centroide_actual.lon]}
                icon={createCentroidIcon('#2563eb')}
              >
                <Popup>Distribución Actual</Popup>
              </Marker>

              {/* Marcador Centroide Futuro */}
              <Marker 
                position={[predictionData.centroide_futuro.lat, predictionData.centroide_futuro.lon]}
                icon={createCentroidIcon('#dc2626')}
              >
                <Popup>Distribución Proyectada (ΔT: {deltaTemp}°C)</Popup>
              </Marker>

              {/* Vector de Migración */}
              <Polyline 
                positions={[
                  [predictionData.centroide_actual.lat, predictionData.centroide_actual.lon],
                  [predictionData.centroide_futuro.lat, predictionData.centroide_futuro.lon]
                ]}
                color="#d97706"
                dashArray="6, 6"
                weight={3}
              />
            </>
          )}
        </MapContainer>
      </div>
    </div>
  );
}