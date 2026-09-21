import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function ReportesView() {
  const [simulaciones, setSimulaciones] = useState([]);
  const [selectedSim, setSelectedSim] = useState('');
  const [previewData, setPreviewData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchSimulaciones = async () => {
      try {
        const res = await api.get('/simulacion/historial');
        if (res.data.success) {
          setSimulaciones(res.data.data);
          // Si hay datos, auto-seleccionamos el primero
          if (res.data.data.length > 0) {
            cargarPreview(res.data.data[0].id_simulacion.toString());
          }
        }
      } catch (err) {
        console.error("Error cargando simulaciones", err);
      }
    };
    fetchSimulaciones();
  }, []);

  const cargarPreview = async (id) => {
    if (!id) return;
    setSelectedSim(id);
    setLoading(true);
    try {
      const res = await api.get(`/reportes/preview/${id}`);
      if (res.data.success) setPreviewData(res.data.data);
    } catch (err) {
      console.error("Error cargando vista previa", err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (formato) => {
    try {
      const res = await api.get(`/reportes/descargar/${selectedSim}?formato=${formato}`, {
        responseType: 'blob' 
      });
      
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      const extension = formato === 'word' ? 'docx' : formato === 'excel' ? 'xlsx' : 'pdf';
      link.setAttribute('download', `Reporte_Conectividad_${selectedSim}.${extension}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error(`Error descargando el reporte en ${formato}:`, err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Cabecera */}
      <div className="bg-gradient-to-r from-slate-800 to-slate-600 dark:from-slate-900 dark:to-slate-800 rounded-xl p-6 text-white shadow-md transition-colors duration-200">
        <h1 className="text-2xl font-bold">📄 Generación de Reportes</h1>
        <p className="mt-2 text-slate-200 dark:text-slate-400">Exportación de resultados de conectividad en PDF, Word y Excel.</p>
      </div>

      {/* Contenedor Principal */}
      <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 transition-colors duration-200">
        
        {/* Combobox de Selección */}
        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
          Seleccionar Simulación a Exportar:
        </label>
        <select 
          value={selectedSim} 
          onChange={(e) => cargarPreview(e.target.value)}
          disabled={simulaciones.length === 0}
          className="w-full md:w-1/2 bg-white dark:bg-slate-900 text-slate-900 dark:text-white border-gray-300 dark:border-slate-600 rounded-md shadow-sm focus:ring-emerald-500 dark:focus:ring-emerald-400 p-2 border mb-6 outline-none transition-colors disabled:opacity-50"
        >
          {simulaciones.length === 0 ? (
            <option value="">No hay simulaciones en la base de datos...</option>
          ) : (
            simulaciones.map(sim => (
              <option key={sim.id_simulacion} value={sim.id_simulacion}>
                {sim.especie_nombre} - Escenario: {sim.escenario} ({new Date(sim.fecha).toLocaleDateString()})
              </option>
            ))
          )}
        </select>

        {/* Zona de Vista Previa */}
        {loading ? (
          <p className="text-center text-slate-500 dark:text-slate-400 py-10 animate-pulse">Cargando vista previa...</p>
        ) : previewData ? (
          <div className="space-y-8 animate-fadeIn">
            
            {/* Botones de Descarga */}
            <div className="flex flex-wrap gap-4 pb-6 border-b border-gray-200 dark:border-slate-700 transition-colors">
              <button onClick={() => handleDownload('pdf')} className="flex items-center gap-2 bg-red-600 hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-600 text-white px-4 py-2 rounded-lg font-medium transition-colors">
                📥 Descargar PDF
              </button>
              <button onClick={() => handleDownload('word')} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 text-white px-4 py-2 rounded-lg font-medium transition-colors">
                📥 Descargar Word
              </button>
              <button onClick={() => handleDownload('excel')} className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-700 dark:hover:bg-emerald-600 text-white px-4 py-2 rounded-lg font-medium transition-colors">
                📥 Descargar Excel
              </button>
            </div>

            {/* Vista Previa: Resumen Ejecutivo */}
            <div>
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 mb-2">👁️ Vista Previa: Resumen Ejecutivo</h3>
              <div className="p-4 bg-slate-50 dark:bg-slate-900/50 border border-slate-100 dark:border-slate-700/50 rounded-lg text-slate-700 dark:text-slate-300 text-sm leading-relaxed transition-colors">
                {previewData.resumen_ejecutivo}
              </div>
            </div>

            {/* Vista Previa: Gráficos */}
            <div>
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 mb-4">📈 Evolución de la Probabilidad de Conectividad (PC)</h3>
              <div className="h-80 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={previewData.metricas_temporales}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.3} stroke="#94a3b8" />
                    <XAxis dataKey="año" stroke="#64748b" />
                    <YAxis domain={['auto', 'auto']} stroke="#64748b" />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc', borderRadius: '8px' }}
                      itemStyle={{ color: '#e2e8f0' }}
                    />
                    <Legend wrapperStyle={{ paddingTop: '10px' }}/>
                    <Line type="monotone" dataKey="estatico_pc" stroke="#ef4444" name="Diseño Estático" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                    <Line type="monotone" dataKey="dinamico_pc" stroke="#10b981" name="Diseño Dinámico" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-center text-slate-500 dark:text-slate-400 py-10">No hay datos disponibles para mostrar.</p>
        )}
      </div>
    </div>
  );
}