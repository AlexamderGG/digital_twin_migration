import { useState, useEffect } from 'react';
import api from '../services/api';

export default function Conectividad() {
  const [especies, setEspecies] = useState([]);
  const [selectedEspecie, setSelectedEspecie] = useState('');
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchEspecies = async () => {
      try {
        const res = await api.get('/datos/especies');
        if (res.data.success && res.data.data.length > 0) {
          setEspecies(res.data.data);
          setSelectedEspecie(res.data.data[0].id_especie);
        }
      } catch (err) {
        console.error("Error cargando especies", err);
      }
    };
    fetchEspecies();
  }, []);

  const ejecutarAnalisis = async () => {
    if (!selectedEspecie) return;
    setLoading(true);
    setError('');
    
    try {
      const res = await api.post('/conectividad/analizar', {
        id_especie: parseInt(selectedEspecie),
        codigo_ssp: 'SSP2-4.5' // Valor por defecto
      });
      
      if (res.data.success) {
        setResultado(res.data.data);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al procesar la conectividad funcional.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-blue-900 to-blue-600 rounded-xl p-6 text-white shadow-md">
        <h1 className="text-2xl font-bold">⚡ Conectividad Funcional</h1>
        <p className="mt-2 text-blue-100">
          Análisis mediante Teoría de Circuitos y métricas de paisaje.
        </p>
      </div>

      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
        <div className="max-w-md mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">Especie a analizar</label>
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

        <button 
          onClick={ejecutarAnalisis}
          disabled={loading}
          className="bg-blue-600 text-white font-medium py-2 px-6 rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Calculando matriz laplaciana...' : '🔬 Ejecutar Análisis de Conectividad'}
        </button>

        {error && <p className="text-red-500 mt-4 text-sm">{error}</p>}

        {resultado && !loading && (
          <div className="mt-8 grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-gray-50 p-4 rounded-lg text-center border">
              <div className="text-sm text-gray-500">PC (Prob. Conectividad)</div>
              <div className="text-2xl font-bold text-blue-900">{resultado.pc.toFixed(6)}</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg text-center border">
              <div className="text-sm text-gray-500">IIC</div>
              <div className="text-2xl font-bold text-blue-900">{resultado.iic.toFixed(6)}</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg text-center border">
              <div className="text-sm text-gray-500">EC</div>
              <div className="text-2xl font-bold text-blue-900">{resultado.ec.toFixed(2)}</div>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg text-center border">
              <div className="text-sm text-gray-500">Corriente Total</div>
              <div className="text-2xl font-bold text-blue-900">{resultado.corriente_total.toFixed(4)}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}