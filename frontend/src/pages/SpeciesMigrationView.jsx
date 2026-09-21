import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, GeoJSON, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import api from '../services/api';

const createCentroidIcon = (color) => L.divIcon({
  className: 'custom-centroid-marker',
  html: `<div style="background-color: ${color}; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 4px rgba(0,0,0,0.5);"></div>`,
  iconSize: [14, 14],
  iconAnchor: [7, 7]
});

const REGIONES = [
  { id: 'amazonia', nombre: 'Amazonía y Andes', bounds: [-80, -15, -60, 5] },
  { id: 'costa_pacifica', nombre: 'Costa Pacífica (Tortugas/Aves marinas)', bounds: [-95, -40, -70, 15] },
  { id: 'sudamerica', nombre: 'Sudamérica Completa (Lento)', bounds: [-85, -55, -35, 15] },
  { id: 'mesoamerica', nombre: 'Mesoamérica', bounds: [-95, 5, -75, 20] }
];

// Componente para auto-enfocar los resultados generados
function MapUpdater({ data }) {
  const map = useMap();
  useEffect(() => {
    if (data && data.geojson_actual) {
      try {
        const capaActual = L.geoJSON(data.geojson_actual);
        const limites = capaActual.getBounds();
        if (data.geojson_futuro) {
           const capaFutura = L.geoJSON(data.geojson_futuro);
           limites.extend(capaFutura.getBounds());
        }
        if (limites.isValid()) {
          map.flyToBounds(limites, { padding: [50, 50], duration: 1.5 });
        }
      } catch (e) {
        console.error("Error al enfocar:", e);
      }
    }
  }, [data, map]);
  return null;
}

// Componente para previsualizar la región antes de simular
function RegionPreviewer({ regionId, hasData }) {
  const map = useMap();
  useEffect(() => {
    if (!hasData && regionId) {
      const region = REGIONES.find(r => r.id === regionId);
      if (region) {
        const [minX, minY, maxX, maxY] = region.bounds;
        map.flyToBounds([[minY, minX], [maxY, maxX]], { padding: [20, 20], duration: 1.0 });
      }
    }
  }, [regionId, hasData, map]);
  return null;
}

export default function SpeciesMigrationView() {
  const [especies, setEspecies] = useState([]);
  const [selectedEspecie, setSelectedEspecie] = useState('');
  const [selectedRegion, setSelectedRegion] = useState('amazonia');
  const [deltaTemp, setDeltaTemp] = useState(1.5);
  const [loading, setLoading] = useState(false);
  const [predictionData, setPredictionData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchEspecies = async () => {
      try {
        const res = await api.get('/datos/especies');
        if (res.data.success && res.data.data.length > 0) {
          setEspecies(res.data.data);
          setSelectedEspecie(res.data.data[0].id_especie.toString()); 
        }
      } catch (err) {}
    };
    fetchEspecies();
  }, []);

  useEffect(() => {
    if (selectedEspecie === '2' || selectedEspecie === '3') {
      setSelectedRegion('costa_pacifica');
    } else {
      setSelectedRegion('amazonia');
    }
  }, [selectedEspecie]);

  const handlePredecir = async () => {
    if (!selectedEspecie) return;
    setLoading(true);
    setError('');
    setPredictionData(null);

    const regionBounds = REGIONES.find(r => r.id === selectedRegion)?.bounds || [-80, -15, -60, 5];

    try {
      const response = await api.post('/habitat/predecir-migracion', {
        id_especie: parseInt(selectedEspecie),
        delta_temp: parseFloat(deltaTemp),
        criterio_optimo: 'auc',
        bounds: regionBounds // NUEVO PARÁMETRO ENVIADO AL BACKEND
      });
      
      const dataToSet = response.data.data ? response.data.data : response.data;
      setPredictionData(dataToSet);

    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Error de conexión.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col lg:flex-row h-screen bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-200 transition-colors duration-200">
      <div className="w-full lg:w-96 p-6 bg-white dark:bg-slate-800 shadow-md z-10 flex flex-col gap-5 overflow-y-auto border-r border-transparent dark:border-slate-700 transition-colors duration-200">
        <div>
          <h2 className="text-xl font-bold text-emerald-800 dark:text-emerald-500">🌿 Predicción de Migración</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">Gemelo Digital Climático</p>
        </div>

        <div>
          <label className="block text-sm font-semibold mb-1 dark:text-slate-300">Especie Objetivo:</label>
          <select 
            value={selectedEspecie} 
            onChange={(e) => setSelectedEspecie(e.target.value)}
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg p-2 text-sm bg-slate-50 dark:bg-slate-900 dark:text-white focus:ring-2 focus:ring-emerald-500 outline-none"
          >
            {especies.map(esp => (
              <option key={esp.id_especie} value={esp.id_especie}>
                {esp.nombre_cientifico} ({esp.nombre_comun || 'Sin nombre común'})
              </option>
            ))}
          </select>
        </div>

        {/* NUEVO SELECTOR DE REGIÓN */}
        <div>
          <label className="block text-sm font-semibold mb-1 dark:text-slate-300">Región de Análisis:</label>
          <select 
            value={selectedRegion} 
            onChange={(e) => setSelectedRegion(e.target.value)}
            className="w-full border border-slate-300 dark:border-slate-600 rounded-lg p-2 text-sm bg-slate-50 dark:bg-slate-900 dark:text-white focus:ring-2 focus:ring-emerald-500 outline-none"
          >
            {REGIONES.map(r => (
              <option key={r.id} value={r.id}>{r.nombre}</option>
            ))}
          </select>
        </div>

        <div className="bg-slate-100 dark:bg-slate-700/50 p-4 rounded-xl transition-colors">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-semibold dark:text-slate-200">Variación Temperatura:</span>
            <span className={`text-sm font-extrabold ${deltaTemp >= 0 ? 'text-rose-600 dark:text-rose-400' : 'text-blue-600 dark:text-blue-400'}`}>
              {deltaTemp > 0 ? `+${deltaTemp}` : deltaTemp} °C
            </span>
          </div>
          <input 
            type="range" min="-2.0" max="4.0" step="0.5" 
            value={deltaTemp} onChange={(e) => setDeltaTemp(e.target.value)}
            className="w-full accent-emerald-600 dark:accent-emerald-500 cursor-pointer"
          />
        </div>

        <button
          onClick={handlePredecir}
          disabled={loading}
          className="w-full py-2.5 bg-emerald-700 dark:bg-emerald-600 hover:bg-emerald-800 text-white font-medium rounded-lg shadow transition disabled:opacity-50"
        >
          {loading ? 'Calculando migración...' : 'Simular Migración'}
        </button>
        
        {error && (
          <div className="mt-3 bg-rose-50 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 p-3 rounded-lg text-sm border border-rose-200 dark:border-rose-800">
            <strong>Atención:</strong> {error}
          </div>
        )}

        {predictionData && (
          <div className="flex flex-col gap-3 mt-2 border-t dark:border-slate-700 pt-4 text-sm animate-fadeIn">
            <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-lg">
              <span className="text-xs text-emerald-600 dark:text-emerald-500 font-bold uppercase block">
                Mejor Modelo Autoseleccionado
              </span>
              <p className="font-semibold text-emerald-900 dark:text-emerald-300">{predictionData.mejor_modelo.nombre}</p>
            </div>
            <div className="grid grid-cols-2 gap-2 text-center">
              <div className="p-2.5 bg-slate-100 dark:bg-slate-700/50 rounded-lg">
                <span className="text-xs text-slate-500 dark:text-slate-400 block">Desplazamiento</span>
                <span className="font-bold text-slate-800 dark:text-slate-200">{predictionData.metricas.distancia_km} km</span>
              </div>
              <div className="p-2.5 bg-slate-100 dark:bg-slate-700/50 rounded-lg">
                <span className="text-xs text-slate-500 dark:text-slate-400 block">Cambio Hábitat</span>
                <span className={`font-bold ${predictionData.metricas.cambio_superficie_pct >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                  {predictionData.metricas.cambio_superficie_pct > 0 ? '+' : ''}{predictionData.metricas.cambio_superficie_pct}%
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="flex-1 h-full relative z-0">
        <MapContainer center={[-9.19, -75.01]} zoom={5} className="w-full h-full">
          <TileLayer
            attribution='&copy; OpenStreetMap'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <RegionPreviewer regionId={selectedRegion} hasData={!!predictionData} />
          <MapUpdater data={predictionData} />

          {predictionData && (
            <>
              {predictionData.geojson_actual && (
                <GeoJSON data={predictionData.geojson_actual} style={{ color: '#2563eb', weight: 1.5, fillOpacity: 0.25 }} />
              )}
              {predictionData.geojson_futuro && (
                <GeoJSON data={predictionData.geojson_futuro} style={{ color: '#dc2626', weight: 1.5, fillOpacity: 0.35 }} />
              )}
              {predictionData.centroide_actual && (
                <Marker position={[predictionData.centroide_actual.lat, predictionData.centroide_actual.lon]} icon={createCentroidIcon('#2563eb')}><Popup>Actual</Popup></Marker>
              )}
              {predictionData.centroide_futuro && (
                <Marker position={[predictionData.centroide_futuro.lat, predictionData.centroide_futuro.lon]} icon={createCentroidIcon('#dc2626')}><Popup>Futuro</Popup></Marker>
              )}
              {predictionData.centroide_actual && predictionData.centroide_futuro && (
                <Polyline positions={[[predictionData.centroide_actual.lat, predictionData.centroide_actual.lon], [predictionData.centroide_futuro.lat, predictionData.centroide_futuro.lon]]} color="#d97706" dashArray="6, 6" weight={3} />
              )}
            </>
          )}
        </MapContainer>
      </div>
    </div>
  );
}