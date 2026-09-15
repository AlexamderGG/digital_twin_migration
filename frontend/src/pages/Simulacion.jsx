import { useState, useEffect } from 'react';
import api from '../services/api'; 

export default function Simulacion() {
  const [especies, setEspecies] = useState([]);
  const [selectedEspecie, setSelectedEspecie] = useState('');
  const [ssp, setSsp] = useState('SSP2-4.5');
  const [yearStart, setYearStart] = useState(2024);
  const [yearEnd, setYearEnd] = useState(2050);
  
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchEspecies = async () => {
      try {
        const res = await api.get('/datos/especies');
        if (res.data.success && res.data.data.length > 0) {
          setEspecies(res.data.data);
          setSelectedEspecie(res.data.data[0].id_especie.toString());
        }
      } catch (err) {
        console.error("Error cargando especies", err);
        setError('No se pudieron cargar las especies de la base de datos.');
      }
    };
    fetchEspecies();
  }, []);

  const handleSimular = async (e) => {
    e.preventDefault();
    
    if (!selectedEspecie) {
      setError('Debes seleccionar una especie.');
      return;
    }
    if (parseInt(yearStart) >= parseInt(yearEnd)) {
      setError('El año de inicio debe ser menor al año de fin.');
      return;
    }
    
    setLoading(true);
    setError('');
    setResultado(null);

    try {
      const res = await api.post('/simulacion/ejecutar', {
        id_especie: parseInt(selectedEspecie),
        codigo_ssp: ssp,
        año_inicio: parseInt(yearStart),
        año_fin: parseInt(yearEnd)
      });
      
      if (res.data.success) {
        console.log("📦 PAQUETE DEL BACKEND:", res.data.data); // Nuestro espía
        setResultado(res.data.data);
      }
    } catch (err) {
      const mensajeError = err.response?.data?.detail || err.message || 'Error en la conexión con el servidor.';
      setError(mensajeError);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-blue-900 to-blue-600 rounded-xl p-6 text-white shadow-md">
        <h1 className="text-2xl font-bold">🌍 Simulación de Escenarios Climáticos</h1>
        <p className="mt-2 text-blue-100">
          Comparación de conectividad funcional bajo rutas socioeconómicas compartidas (SSP).
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Panel de Configuración */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 lg:col-span-1">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Parámetros</h2>
          <form onSubmit={handleSimular} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Especie</label>
              <select 
                value={selectedEspecie} 
                onChange={(e) => setSelectedEspecie(e.target.value)}
                className="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 p-2 border"
              >
                {especies.map(e => (
                  <option key={e.id_especie} value={e.id_especie}>
                    {e.nombre_cientifico}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Escenario Climático (SSP)</label>
              <select 
                value={ssp} 
                onChange={(e) => setSsp(e.target.value)}
                className="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 p-2 border"
              >
                <option value="SSP1-2.6">🌱 SSP1-2.6 (Sostenibilidad)</option>
                <option value="SSP2-4.5">⚖️ SSP2-4.5 (Intermedio)</option>
                <option value="SSP5-8.5">🏭 SSP5-8.5 (Alto consumo)</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Año Inicio</label>
                <input 
                  type="number" 
                  value={yearStart}
                  onChange={(e) => setYearStart(e.target.value)}
                  className="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 p-2 border"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Año Fin</label>
                <input 
                  type="number" 
                  value={yearEnd}
                  onChange={(e) => setYearEnd(e.target.value)}
                  className="w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 p-2 border"
                />
              </div>
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full bg-blue-600 text-white font-medium py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 mt-4"
            >
              {loading ? 'Simulando escenario...' : '🚀 Ejecutar Comparación'}
            </button>
          </form>

          {error && (
            <div className="mt-4 bg-red-50 text-red-600 p-3 rounded-md text-sm border border-red-200">
              {error}
            </div>
          )}
        </div>

        {/* Panel de Resultados */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 lg:col-span-2 flex flex-col items-center justify-center min-h-[300px]">
          {loading ? (
            <div className="text-blue-600 animate-pulse flex flex-col items-center">
              <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-4"></div>
              <p>Procesando conectividad del paisaje. Esto puede tomar unos momentos...</p>
            </div>
          ) : resultado ? (
            <div className={`w-full p-8 rounded-xl border-l-4 ${resultado.hipotesis_soportada ? 'bg-green-50 border-green-500' : 'bg-yellow-50 border-yellow-500'}`}>
              <h2 className={`text-2xl font-bold mb-2 ${resultado.hipotesis_soportada ? 'text-green-700' : 'text-yellow-700'}`}>
                {resultado.hipotesis_soportada ? '✅ HIPÓTESIS SOPORTADA' : '⚠️ RESULTADO PARCIAL'}
              </h2>
              <p className="text-lg text-gray-700 mt-4">
                Mejora promedio en conectividad: <strong className="text-2xl">{resultado.mejora_pc_promedio.toFixed(2)}%</strong>
              </p>
              <p className="text-gray-600 mt-2">
                {resultado.hipotesis_soportada 
                  ? 'El diseño dinámico supera el umbral del 25% establecido en la hipótesis.' 
                  : 'No se alcanza el umbral del 25% de mejora en este escenario.'}
              </p>
              <div className="mt-6 pt-4 border-t border-gray-200 text-sm text-gray-500">
                Especie: {resultado.especie} | Escenario: {resultado.escenario}
              </div>
              {/* MAPA */}
              {resultado.url_mapa_resultado && (
                <img src={`http://localhost:8000${resultado.url_mapa_resultado}`} alt="Mapa Resultado" className="w-full h-auto mt-4" />
              )}
            </div>
          ) : (
             <div className="text-center text-gray-400">
                <p>Configura los parámetros y ejecuta la simulación para comparar los corredores estáticos vs. dinámicos.</p>
             </div>
          )}
        </div>
      </div>
    </div>
  );
}