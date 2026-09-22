import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useTranslation } from 'react-i18next';

export default function ReportesView() {
  const { t, i18n } = useTranslation();
  const [simulaciones, setSimulaciones] = useState([]);
  const [selectedSim, setSelectedSim] = useState('');
  const [previewData, setPreviewData] = useState(null);
  const [pdfBlobUrl, setPdfBlobUrl] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchSimulaciones = async () => {
      try {
        const res = await api.get('/simulacion/historial');
        if (res.data.success) {
          setSimulaciones(res.data.data);
          if (res.data.data.length > 0) {
            setSelectedSim(res.data.data[0].id_simulacion.toString());
          }
        }
      } catch (err) {
        console.error("Error cargando simulaciones", err);
      }
    };
    fetchSimulaciones();
  }, []);

  useEffect(() => {
    if (selectedSim) {
      cargarPreview(selectedSim);
    }
    
    return () => {
      if (pdfBlobUrl) {
        window.URL.revokeObjectURL(pdfBlobUrl);
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedSim, i18n.language]);

  const cargarPreview = async (id) => {
    if (!id) return;
    setLoading(true);
    
    // 1. Sintaxis corregida usando ${}
    try {
      const res = await api.get(`/reportes/preview/${id}?lang=${i18n.language}`);
      if (res.data.success) {
        setPreviewData(res.data.data);
      } else {
        setPreviewData(null);
      }
    } catch (err) {
      console.error("Error cargando datos de la vista previa:", err);
      setPreviewData(null);
    }

    // 2. Sintaxis corregida usando ${}
    try {
      const pdfRes = await api.get(`/reportes/descargar/${id}?formato=pdf&lang=${i18n.language}`, {
        responseType: 'blob'
      });
      if (pdfBlobUrl) window.URL.revokeObjectURL(pdfBlobUrl);
      const url = window.URL.createObjectURL(new Blob([pdfRes.data], { type: 'application/pdf' }));
      setPdfBlobUrl(url);
    } catch (err) {
      console.error("Error cargando el PDF embebido desde el backend:", err);
      setPdfBlobUrl(null);
    }

    setLoading(false);
  };

  const handleDownload = async (formato) => {
    // 3. Sintaxis corregida usando ${}
    try {
      const res = await api.get(`/reportes/descargar/${selectedSim}?formato=${formato}&lang=${i18n.language}`, {
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
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(`Error descargando el reporte en ${formato}:`, err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-slate-800 to-slate-600 dark:from-slate-900 dark:to-slate-800 rounded-xl p-6 text-white shadow-md transition-colors duration-200">
        <h1 className="text-2xl font-bold">📄 {t('reports.title')}</h1>
        <p className="mt-2 text-slate-200 dark:text-slate-400">{t('reports.subtitle')}</p>
      </div>

      <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 transition-colors duration-200">
        
        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
          {t('reports.select_label')}
        </label>
        <select 
          value={selectedSim} 
          onChange={(e) => setSelectedSim(e.target.value)}
          disabled={simulaciones.length === 0}
          className="w-full md:w-1/2 bg-white dark:bg-slate-900 text-slate-900 dark:text-white border-gray-300 dark:border-slate-600 rounded-md shadow-sm focus:ring-emerald-500 dark:focus:ring-emerald-400 p-2 border mb-6 outline-none transition-colors disabled:opacity-50"
        >
          {simulaciones.length === 0 ? (
            <option value="">{t('reports.no_simulations')}</option>
          ) : (
            simulaciones.map(sim => (
              <option key={sim.id_simulacion} value={sim.id_simulacion}>
                {sim.especie_nombre} - {t('reports.scenario')}: {sim.escenario} ({new Date(sim.fecha).toLocaleDateString()})
              </option>
            ))
          )}
        </select>

        {loading ? (
          <p className="text-center text-slate-500 dark:text-slate-400 py-10 animate-pulse">{t('reports.loading_preview')}</p>
        ) : previewData ? (
          <div className="space-y-8 animate-fadeIn">
            
            <div className="flex flex-wrap gap-4 pb-6 border-b border-gray-200 dark:border-slate-700 transition-colors">
              <button onClick={() => handleDownload('pdf')} className="flex items-center gap-2 bg-red-600 hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-600 text-white px-4 py-2 rounded-lg font-medium transition-colors">
                📥 {t('reports.btn_pdf')}
              </button>
              <button onClick={() => handleDownload('word')} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 text-white px-4 py-2 rounded-lg font-medium transition-colors">
                📥 {t('reports.btn_word')}
              </button>
              <button onClick={() => handleDownload('excel')} className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-700 dark:hover:bg-emerald-600 text-white px-4 py-2 rounded-lg font-medium transition-colors">
                📥 {t('reports.btn_excel')}
              </button>
            </div>

            <div>
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 mb-2">👁️ {t('reports.preview_summary')}</h3>
              <div className="p-4 bg-slate-50 dark:bg-slate-900/50 border border-slate-100 dark:border-slate-700/50 rounded-lg text-slate-700 dark:text-slate-300 text-sm leading-relaxed transition-colors">
                {previewData.resumen_ejecutivo}
              </div>
            </div>

            <div>
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 mb-4">📈 {t('reports.preview_chart')}</h3>
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
                    <Line type="monotone" dataKey="estatico_pc" stroke="#ef4444" name={t('reports.static_design')} strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                    <Line type="monotone" dataKey="dinamico_pc" stroke="#10b981" name={t('reports.dynamic_design')} strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="pt-6 border-t border-gray-200 dark:border-slate-700 transition-colors">
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 mb-4">📑 {t('reports.preview_pdf')}</h3>
              <div className="w-full h-[700px] border border-gray-300 dark:border-slate-600 rounded-lg overflow-hidden bg-slate-100 dark:bg-slate-900 shadow-inner">
                {pdfBlobUrl ? (
                  <iframe 
                    src={`${pdfBlobUrl}#toolbar=1&navpanes=0&view=FitH`} 
                    className="w-full h-full border-none"
                    title="Visor PDF"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-600 dark:border-slate-400"></div>
                  </div>
                )}
              </div>
            </div>

          </div>
        ) : (
          <p className="text-center text-slate-500 dark:text-slate-400 py-10">{t('reports.no_data')}</p>
        )}
      </div>
    </div>
  );
}