import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function ReportesView() {
  const [simulaciones, setSimulaciones] = useState([]);
  const [selectedSim, setSelectedSim] = useState('');
  const [previewData, setPreviewData] = useState(null);
  const [loading, setLoading] = useState(false);

  // 1. Cargar el historial de simulaciones disponibles
  useEffect(() => {
    const fetchSimulaciones = async () => {
      try {
        const res = await api.get('/simulacion/historial');
        if (res.data.success) {
          setSimulaciones(res.data.data);
          if (res.data.data.length > 0) cargarPreview(res.data.data[0].id_simulacion);
        }
      } catch (err) {
        console.error("Error cargando simulaciones", err);
      }
    };
    fetchSimulaciones();
  }, []);

  // 2. Cargar datos de la simulación seleccionada para la Vista Previa
  const cargarPreview = async (id) => {
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

  // 3. Manejador para descargar archivos (PDF, Word, Excel)
  const handleDownload = async (formato) => {
    try {
      const res = await api.get(`/reportes/descargar/${selectedSim}?formato=${formato}`, {
        responseType: 'blob' // CRÍTICO: Le dice a Axios que recibiremos un archivo
      });
      
      // Crear un enlace temporal para forzar la descarga en el navegador
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      // Asignar extensión correcta según el formato
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
      <div className="bg-gradient-to-r from-slate-800 to-slate-600 rounded-xl p-6 text-white shadow-md">
        <h1 className="text-2xl font-bold">📄 Generación de Reportes</h1>
        <p className="mt-2 text-slate-200">Exportación de resultados de conectividad en PDF, Word y Excel.</p>
      </div>

      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
        <label className="block text-sm font-medium text-gray-700 mb-2">Seleccionar Simulación a Exportar:</label>
        <select 
          value={selectedSim} 
          onChange={(e) => cargarPreview(e.target.value)}
          className="w-full md:w-1/2 border-gray-300 rounded-md shadow-sm focus:ring-emerald-500 p-2 border mb-6"
        >
          {simulaciones.map(sim => (
            <option key={sim.id_simulacion} value={sim.id_simulacion}>
              {sim.especie_nombre} - Escenario: {sim.escenario} ({new Date(sim.fecha).toLocaleDateString()})
            </option>
          ))}
        </select>

        {loading ? (
          <p className="text-center text-slate-500 py-10">Cargando vista previa...</p>
        ) : previewData ? (
          <div className="space-y-8">
            {/* Botones de Descarga */}
            <div className="flex flex-wrap gap-4 pb-6 border-b">
              <button onClick={() => handleDownload('pdf')} className="flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-medium transition">
                📥 Descargar PDF
              </button>
              <button onClick={() => handleDownload('word')} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition">
                📥 Descargar Word
              </button>
              <button onClick={() => handleDownload('excel')} className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium transition">
                📥 Descargar Excel
              </button>
            </div>

            {/* Vista Previa: Resumen Ejecutivo */}
            <div>
              <h3 className="text-lg font-bold text-slate-800 mb-2">👁️ Vista Previa: Resumen Ejecutivo</h3>
              <div className="p-4 bg-slate-50 border border-slate-100 rounded-lg text-slate-700 text-sm leading-relaxed">
                {previewData.resumen_ejecutivo}
              </div>
            </div>

            {/* Vista Previa: Gráficos */}
            <div>
              <h3 className="text-lg font-bold text-slate-800 mb-4">📈 Evolución de la Probabilidad de Conectividad (PC)</h3>
              <div className="h-80 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={previewData.metricas_temporales}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.5} />
                    <XAxis dataKey="año" />
                    <YAxis domain={['auto', 'auto']} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="estatico_pc" stroke="#dc2626" name="Diseño Estático" strokeWidth={2} />
                    <Line type="monotone" dataKey="dinamico_pc" stroke="#16a34a" name="Diseño Dinámico" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-center text-slate-500 py-10">No hay datos disponibles para mostrar.</p>
        )}
      </div>
    </div>
  );
}