import { useState, useEffect } from 'react';
import api from '../services/api'; 
import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch";
import { useTranslation } from 'react-i18next';

export default function Simulacion() {
  const { t } = useTranslation();
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
        setError(t('simulation.errors.load_species'));
      }
    };
    fetchEspecies();
  }, [t]);

  const handleSimular = async (e) => {
    e.preventDefault();
    
    if (!selectedEspecie) {
      setError(t('simulation.errors.select_species'));
      return;
    }
    if (parseInt(yearStart) >= parseInt(yearEnd)) {
      setError(t('simulation.errors.invalid_years'));
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
        setResultado(res.data.data);
      }
    } catch (err) {
      const mensajeError = err.response?.data?.detail || err.message || t('simulation.errors.connection');
      setError(mensajeError);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-blue-900 to-blue-600 rounded-xl p-6 text-white shadow-md">
        <h1 className="text-2xl font-bold">{t('simulation.title')}</h1>
        <p className="mt-2 text-blue-100">
          {t('simulation.subtitle')}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 lg:col-span-1 transition-colors duration-200">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-slate-100 mb-4">{t('simulation.parameters_title')}</h2>
          <form onSubmit={handleSimular} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">{t('simulation.species_label')}</label>
              <select 
                value={selectedEspecie} 
                onChange={(e) => setSelectedEspecie(e.target.value)}
                className="w-full bg-white dark:bg-slate-900 text-slate-900 dark:text-white border-gray-300 dark:border-slate-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 p-2 border transition-colors"
              >
                {especies.map(e => (
                  <option key={e.id_especie} value={e.id_especie}>
                    {e.nombre_cientifico}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">{t('simulation.ssp_label')}</label>
              <select 
                value={ssp} 
                onChange={(e) => setSsp(e.target.value)}
                className="w-full bg-white dark:bg-slate-900 text-slate-900 dark:text-white border-gray-300 dark:border-slate-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 p-2 border transition-colors"
              >
                <option value="SSP1-2.6">🌱 {t('simulation.ssp_1')}</option>
                <option value="SSP2-4.5">⚖️ {t('simulation.ssp_2')}</option>
                <option value="SSP5-8.5">🏭 {t('simulation.ssp_3')}</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">{t('simulation.year_start')}</label>
                <input 
                  type="number" 
                  value={yearStart}
                  onChange={(e) => setYearStart(e.target.value)}
                  className="w-full bg-white dark:bg-slate-900 text-slate-900 dark:text-white border-gray-300 dark:border-slate-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 p-2 border transition-colors"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">{t('simulation.year_end')}</label>
                <input 
                  type="number" 
                  value={yearEnd}
                  onChange={(e) => setYearEnd(e.target.value)}
                  className="w-full bg-white dark:bg-slate-900 text-slate-900 dark:text-white border-gray-300 dark:border-slate-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 p-2 border transition-colors"
                />
              </div>
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full bg-blue-600 dark:bg-blue-500 text-white font-medium py-2 px-4 rounded-md hover:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 mt-4 transition-colors"
            >
              {loading ? t('simulation.simulating_btn') : t('simulation.execute_btn')}
            </button>
          </form>

          {error && (
            <div className="mt-4 bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 p-3 rounded-md text-sm border border-red-200 dark:border-red-800 transition-colors">
              {error}
            </div>
          )}
        </div>

        <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 lg:col-span-2 flex flex-col items-center justify-center min-h-[300px] transition-colors duration-200">
          {loading ? (
            <div className="text-blue-600 dark:text-blue-400 animate-pulse flex flex-col items-center">
              <div className="w-12 h-12 border-4 border-blue-600 dark:border-blue-400 border-t-transparent dark:border-t-transparent rounded-full animate-spin mb-4"></div>
              <p>{t('simulation.processing')}</p>
            </div>
          ) : resultado ? (
            <div className={`w-full p-8 rounded-xl border-l-4 transition-colors ${
              resultado.hipotesis_soportada 
                ? 'bg-green-50 dark:bg-green-900/20 border-green-500' 
                : 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-500'
            }`}>
              <h2 className={`text-2xl font-bold mb-2 ${
                resultado.hipotesis_soportada ? 'text-green-700 dark:text-green-400' : 'text-yellow-700 dark:text-yellow-400'
              }`}>
                {resultado.hipotesis_soportada ? t('simulation.hypothesis_supported') : t('simulation.partial_result')}
              </h2>
              <p className="text-lg text-gray-700 dark:text-slate-200 mt-4">
                {t('simulation.avg_improvement')} <strong className="text-2xl">{resultado.mejora_pc_promedio.toFixed(2)}%</strong>
              </p>
              <p className="text-gray-600 dark:text-slate-300 mt-2">
                {resultado.hipotesis_soportada 
                  ? t('simulation.hypothesis_desc_supported') 
                  : t('simulation.hypothesis_desc_partial')}
              </p>
              <div className="mt-6 pt-4 border-t border-gray-200 dark:border-slate-600 text-sm text-gray-500 dark:text-slate-400 transition-colors">
                {t('simulation.species_result')} {resultado.especie} | {t('simulation.scenario_result')} {resultado.escenario}
              </div>
              
              {resultado.url_mapa_resultado && (
                <div className="mt-6 flex flex-col items-center w-full">
                  <p className="text-sm text-slate-500 dark:text-slate-400 mb-2 flex items-center gap-2">
                    <span>🔍</span> {t('simulation.map_instructions')}
                  </p>
                  
                  <div className="w-full h-[60vh] min-h-[400px] overflow-hidden rounded-xl border border-gray-200 dark:border-slate-600 bg-white shadow-inner cursor-move">
                    <TransformWrapper
                      initialScale={1}
                      minScale={0.5}
                      maxScale={8}
                      centerOnInit={true}
                      limitToBounds={false}
                    >
                      <TransformComponent 
                        wrapperStyle={{ width: "100%", height: "100%" }} 
                        contentStyle={{ width: "100%", height: "100%", display: "flex", justifyContent: "center", alignItems: "center" }}
                      >
                        <img 
                          src={`http://localhost:8000${resultado.url_mapa_resultado}`} 
                          alt={t('simulation.map_alt')} 
                          className="max-w-full max-h-full object-contain pointer-events-none" 
                        />
                      </TransformComponent>
                    </TransformWrapper>
                  </div>
                </div>
              )}
            </div>
          ) : (
             <div className="text-center text-gray-400 dark:text-slate-500">
                <p>{t('simulation.empty_state')}</p>
             </div>
          )}
        </div>
      </div>
    </div>
  );
}