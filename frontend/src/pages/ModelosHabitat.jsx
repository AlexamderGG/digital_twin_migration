import { useState, useEffect } from 'react';
import api from '../services/api';

export default function ModelosHabitat() {
  const [especies, setEspecies] = useState([]);
  const [selectedEspecie, setSelectedEspecie] = useState('');
  const [loading, setLoading] = useState(false);
  const [modeloInfo, setModeloInfo] = useState(null);

  // 1. Cargar el catálogo de especies al iniciar
  useEffect(() => {
    if (!selectedEspecie) return;

    const fetchMejorModelo = async () => {
      setLoading(true);
      try {
        const res = await api.get(`/habitat/modelo/${selectedEspecie}`);
        if (res.data.success) {
          setModeloInfo(res.data.data);
        }
      } catch (err) {
        console.error("Error al obtener el modelo:", err);
        setModeloInfo(null); // Limpiamos si no hay modelo en BD
      } finally {
        setLoading(false);
      }
    };

    fetchMejorModelo();
  }, [selectedEspecie]);

  // 2. Cada vez que cambie la especie, buscar su mejor modelo
  useEffect(() => {
    if (!selectedEspecie) return;

    const fetchMejorModelo = async () => {
      setLoading(true);
      // Simulación temporal de la llamada al backend para obtener el modelo pre-entrenado
      setTimeout(() => {
        setModeloInfo({
          algoritmo: 'Random Forest (Mejor Modelo)',
          fecha_entrenamiento: '2026-09-01',
          auc: 0.9214,
          tss: 0.8105,
          accuracy: 0.8842,
          variables_importantes: [
            { nombre: 'Temperatura Media Anual', peso: 0.45 },
            { nombre: 'Precipitación Estacional', peso: 0.32 },
            { nombre: 'Uso de Suelo', peso: 0.23 }
          ]
        });
        setLoading(false);
      }, 800);
    };

    fetchMejorModelo();
  }, [selectedEspecie]);

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-blue-900 to-blue-600 rounded-xl p-6 text-white shadow-md">
        <h1 className="text-2xl font-bold">🗺️ Idoneidad de Hábitat</h1>
        <p className="mt-2 text-blue-100">
          Visualización de las métricas y distribución proyectada utilizando el mejor modelo calibrado.
        </p>
      </div>

      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
        <div className="max-w-md mb-8">
          <label className="block text-sm font-medium text-gray-700 mb-2">Seleccionar Especie para visualizar</label>
          <select 
            value={selectedEspecie} 
            onChange={(e) => setSelectedEspecie(e.target.value)}
            className="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 p-2 border bg-gray-50"
          >
            {especies.map(e => (
              <option key={e.id_especie} value={e.id_especie}>
                {e.nombre_cientifico}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-500 animate-pulse">
            Recuperando datos del modelo...
          </div>
        ) : modeloInfo ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Tarjeta de Métricas */}
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-bold text-gray-800 border-b pb-2">Desempeño del Modelo</h3>
                <p className="text-sm text-gray-500 mt-2">Algoritmo utilizado: <span className="font-semibold text-gray-700">{modeloInfo.algoritmo}</span></p>
                <p className="text-sm text-gray-500">Última calibración: <span className="font-semibold text-gray-700">{modeloInfo.fecha_entrenamiento}</span></p>
              </div>

              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                  <div className="text-xs text-gray-500 uppercase tracking-wide">AUC</div>
                  <div className="text-xl font-bold text-blue-900 mt-1">{modeloInfo.auc.toFixed(4)}</div>
                </div>
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                  <div className="text-xs text-gray-500 uppercase tracking-wide">TSS</div>
                  <div className="text-xl font-bold text-blue-900 mt-1">{modeloInfo.tss.toFixed(4)}</div>
                </div>
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                  <div className="text-xs text-gray-500 uppercase tracking-wide">Accuracy</div>
                  <div className="text-xl font-bold text-blue-900 mt-1">{modeloInfo.accuracy.toFixed(4)}</div>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-bold text-gray-700 mb-3">Variables más influyentes</h4>
                <div className="space-y-3">
                  {modeloInfo.variables_importantes.map((v, i) => (
                    <div key={i}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-600">{v.nombre}</span>
                        <span className="font-medium text-blue-700">{(v.peso * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${v.peso * 100}%` }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Espacio para el Mapa */}
            <div className="bg-gray-100 rounded-xl border border-gray-200 flex items-center justify-center min-h-[300px]">
              <p className="text-gray-500">Aquí integraremos el visor cartográfico (react-leaflet) con la capa de idoneidad.</p>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}