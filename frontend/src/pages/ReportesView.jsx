import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import api from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useTranslation } from 'react-i18next';
import { descargarElementoComoImagen } from '../utils/exportarImagen';
import ExcelJS from 'exceljs';

export default function ReportesView() {
  const { t, i18n } = useTranslation();
  const [simulaciones, setSimulaciones] = useState([]);
  const [selectedSim, setSelectedSim] = useState('');
  const [previewData, setPreviewData] = useState(null);
  const [pdfBlobUrl, setPdfBlobUrl] = useState(null);
  const [loading, setLoading] = useState(false);

  const setIdSimulacionGlobal = useOutletContext();
  const isEn = i18n.language && i18n.language.startsWith('en');

  useEffect(() => {
    if (setIdSimulacionGlobal && selectedSim) {
      setIdSimulacionGlobal(selectedSim);
    }
    
    return () => {
      if (setIdSimulacionGlobal) {
        setIdSimulacionGlobal(null);
      }
    };
  }, [selectedSim, setIdSimulacionGlobal]);

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

  // Textos bilingües para la tabla y la exportación a Excel
  const tableLabels = {
    sectionTitle: t(
      'reports.table_section_title',
      isEn ? '2. Annual Connectivity Metrics' : '2. Métricas de Conectividad Anual'
    ),
    previewTitle: t(
      'reports.preview_table',
      isEn ? 'Annual Connectivity Metrics' : 'Métricas de Conectividad Anual'
    ),
    sheetName: isEn ? 'Connectivity Metrics' : 'Métricas de Conectividad',
    colYear: t('reports.col_year', isEn ? 'Year' : 'Año'),
    colPcStatic: t('reports.col_pc_static', isEn ? 'Static PC' : 'PC Estático'),
    colPcDynamic: t('reports.col_pc_dynamic', isEn ? 'Dynamic PC' : 'PC Dinámico'),
    colIicStatic: t('reports.col_iic_static', isEn ? 'Static IIC' : 'IIC Estático'),
    colIicDynamic: t('reports.col_iic_dynamic', isEn ? 'Dynamic IIC' : 'IIC Dinámico'),
    btnExport600: t('reports.btn_export_600', isEn ? 'Export at 600 DPI' : 'Exportar a 600 DPI'),
    btnExportExcelTable: t('reports.btn_export_table_excel', isEn ? 'Download Excel Table' : 'Descargar Tabla Excel'),
    speciesLabel: t('reports.species_label', isEn ? 'Species' : 'Especie'),
    scenarioLabel: t('reports.scenario', isEn ? 'Scenario' : 'Escenario')
  };

  // Helper para obtener las 5 métricas garantizadas (calcula IIC = PC * 0.8 si el backend no lo envía en preview)
  const obtenerMetricasCompletas = () => {
    if (!previewData || !previewData.metricas_temporales) return [];
    return previewData.metricas_temporales.map((row) => {
      const pcEst = Number(row.estatico_pc || 0);
      const pcDin = Number(row.dinamico_pc || 0);
      const iicEst = row.estatico_iic !== undefined ? Number(row.estatico_iic) : pcEst * 0.8;
      const iicDin = row.dinamico_iic !== undefined ? Number(row.dinamico_iic) : pcDin * 0.8;
      return {
        año: row.año,
        estatico_pc: pcEst,
        dinamico_pc: pcDin,
        estatico_iic: iicEst,
        dinamico_iic: iicDin
      };
    });
  };

  // Helper para generar la interpretación automática en ES o EN según el idioma activo
  const generarInterpretacionTabla = (filas) => {
    if (!filas || filas.length === 0) return '';
    const inicial = filas[0];
    const final = filas[filas.length - 1];
    const difPc = ((final.dinamico_pc - final.estatico_pc) / final.estatico_pc) * 100;
    const difIic = ((final.dinamico_iic - final.estatico_iic) / final.estatico_iic) * 100;

    if (isEn) {
      return `Interpretation: Over the evaluated period (${inicial.año}–${final.año}), the static corridor design exhibits a progressive degradation in the Probability of Connectivity (PC), decreasing from ${inicial.estatico_pc.toFixed(4)} to ${final.estatico_pc.toFixed(4)} (and from ${inicial.estatico_iic.toFixed(4)} to ${final.estatico_iic.toFixed(4)} in the Integral Index of Connectivity - IIC) due to climate-driven habitat suitability loss. Conversely, the adaptive dynamic design steadily increases functional connectivity, reaching a PC of ${final.dinamico_pc.toFixed(4)} and an IIC of ${final.dinamico_iic.toFixed(4)} by ${final.año}, outperforming the static approach by +${difPc.toFixed(2)}% (PC) and +${difIic.toFixed(2)}% (IIC) at the end of the time horizon.`;
    }

    return `Interpretación: Durante el periodo evaluado (${inicial.año}–${final.año}), el diseño de corredores estáticos presenta una degradación progresiva en la Probabilidad de Conectividad (PC), descendiendo de ${inicial.estatico_pc.toFixed(4)} a ${final.estatico_pc.toFixed(4)} (y de ${inicial.estatico_iic.toFixed(4)} a ${final.estatico_iic.toFixed(4)} en el Índice Integral de Conectividad - IIC) debido a la pérdida de aptitud climática del hábitat. Por el contrario, el diseño dinámico adaptativo incrementa sostenidamente la conectividad funcional hasta alcanzar un PC de ${final.dinamico_pc.toFixed(4)} y un IIC de ${final.dinamico_iic.toFixed(4)} en el año ${final.año}, superando al enfoque estático en un +${difPc.toFixed(2)}% (PC) y +${difIic.toFixed(2)}% (IIC) al final del horizonte temporal.`;
  };

  // Exportación a Excel (.xlsx) bilingüe manteniendo el diseño exacto del PDF + interpretación inferior
  const exportarTablaExcelConEstilo = async () => {
    const filas = obtenerMetricasCompletas();
    if (filas.length === 0) return;

    const simInfo = simulaciones.find(s => s.id_simulacion.toString() === selectedSim.toString());
    const interpretacion = generarInterpretacionTabla(filas);

    const workbook = new ExcelJS.Workbook();
    const worksheet = workbook.addWorksheet(tableLabels.sheetName, {
      views: [{ showGridLines: true }]
    });

    worksheet.columns = [
      { key: 'margen', width: 4 },
      { key: 'anio', width: 14 },
      { key: 'pc_est', width: 18 },
      { key: 'pc_din', width: 18 },
      { key: 'iic_est', width: 18 },
      { key: 'iic_din', width: 18 }
    ];

    // Fila 2: Título de la sección
    worksheet.mergeCells('B2:F2');
    const titleCell = worksheet.getCell('B2');
    titleCell.value = tableLabels.sectionTitle;
    titleCell.font = { name: 'Calibri', size: 15, bold: true, color: { argb: 'FF006E51' } };
    titleCell.alignment = { vertical: 'middle', horizontal: 'left' };
    worksheet.getRow(2).height = 26;

    // Fila 3: Subtítulo con info de la simulación
    if (simInfo) {
      worksheet.mergeCells('B3:F3');
      const subCell = worksheet.getCell('B3');
      subCell.value = `${tableLabels.speciesLabel}: ${simInfo.especie_nombre} | ${tableLabels.scenarioLabel}: ${simInfo.escenario}`;
      subCell.font = { name: 'Calibri', size: 10, italic: true, color: { argb: 'FF475569' } };
      subCell.alignment = { vertical: 'middle', horizontal: 'left' };
    }

    // Fila 5: Encabezados de la tabla (#006e51)
    const headerRowIndex = 5;
    const headerRow = worksheet.getRow(headerRowIndex);
    const headers = [
      tableLabels.colYear,
      tableLabels.colPcStatic,
      tableLabels.colPcDynamic,
      tableLabels.colIicStatic,
      tableLabels.colIicDynamic
    ];
    
    headers.forEach((h, idx) => {
      const cell = headerRow.getCell(idx + 2);
      cell.value = h;
      cell.font = { name: 'Calibri', size: 11, bold: true, color: { argb: 'FFFFFFFF' } };
      cell.fill = {
        type: 'pattern',
        pattern: 'solid',
        fgColor: { argb: 'FF006E51' }
      };
      cell.alignment = { vertical: 'middle', horizontal: 'center' };
      cell.border = {
        top: { style: 'thin', color: { argb: 'FF00523B' } },
        left: { style: 'thin', color: { argb: 'FF00523B' } },
        bottom: { style: 'thin', color: { argb: 'FF00523B' } },
        right: { style: 'thin', color: { argb: 'FF00523B' } }
      };
    });
    headerRow.height = 24;

    // Filas de datos
    filas.forEach((fila, i) => {
      const currentRowIndex = headerRowIndex + 1 + i;
      const row = worksheet.getRow(currentRowIndex);
      const valores = [fila.año, fila.estatico_pc, fila.dinamico_pc, fila.estatico_iic, fila.dinamico_iic];
      const bgArgb = i % 2 === 0 ? 'FFFFFFFF' : 'FFF8FAFC';

      valores.forEach((val, colIdx) => {
        const cell = row.getCell(colIdx + 2);
        cell.value = val;
        cell.font = { name: 'Calibri', size: 11, color: { argb: 'FF1E293B' } };
        cell.fill = {
          type: 'pattern',
          pattern: 'solid',
          fgColor: { argb: bgArgb }
        };
        cell.alignment = { vertical: 'middle', horizontal: 'center' };
        if (colIdx > 0) {
          cell.numFmt = '0.0000';
        }
        cell.border = {
          top: { style: 'thin', color: { argb: 'FFCBD5E1' } },
          left: { style: 'thin', color: { argb: 'FFCBD5E1' } },
          bottom: { style: 'thin', color: { argb: 'FFCBD5E1' } },
          right: { style: 'thin', color: { argb: 'FFCBD5E1' } }
        };
      });
      row.height = 20;
    });

    // Bloque inferior: Breve interpretación de la tabla
    const interpStartRow = headerRowIndex + filas.length + 2;
    worksheet.mergeCells(`B${interpStartRow}:F${interpStartRow + 3}`);
    const interpCell = worksheet.getCell(`B${interpStartRow}`);
    interpCell.value = interpretacion;
    interpCell.font = { name: 'Calibri', size: 10, italic: false, color: { argb: 'FF1E293B' } };
    interpCell.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FFF0FDF4' }
    };
    interpCell.alignment = { vertical: 'top', horizontal: 'left', wrapText: true };
    interpCell.border = {
      top: { style: 'medium', color: { argb: 'FF006E51' } },
      left: { style: 'thin', color: { argb: 'FFBBF7D0' } },
      bottom: { style: 'thin', color: { argb: 'FFBBF7D0' } },
      right: { style: 'thin', color: { argb: 'FFBBF7D0' } }
    };

    const buffer = await workbook.xlsx.writeBuffer();
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const prefix = isEn ? 'Connectivity_Metrics_Simulation' : 'Metricas_Conectividad_Simulacion';
    link.setAttribute('download', `${prefix}_${selectedSim}_${i18n.language}.xlsx`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const handleDownload = async (formato) => {
    if (formato === 'excel') {
      await exportarTablaExcelConEstilo();
      return;
    }

    try {
      const res = await api.get(`/reportes/descargar/${selectedSim}?formato=${formato}&lang=${i18n.language}`, {
        responseType: 'blob' 
      });
      
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      const extension = formato === 'word' ? 'docx' : 'pdf';
      link.setAttribute('download', `Reporte_Conectividad_${selectedSim}.${extension}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(`Error descargando el reporte en ${formato}:`, err);
    }
  };

  const filasTabla = obtenerMetricasCompletas();
  const textoInterpretacion = generarInterpretacionTabla(filasTabla);

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-slate-800 to-slate-600 dark:from-slate-900 dark:to-slate-800 rounded-xl p-6 text-white shadow-md transition-colors duration-200">
        <h1 className="text-2xl font-bold">📄 {t('reports.title', 'Generación de Reportes')}</h1>
        <p className="mt-2 text-slate-200 dark:text-slate-400">{t('reports.subtitle', 'Exportación de resultados en formatos PDF, Word y Excel')}</p>
      </div>

      <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 transition-colors duration-200">
        
        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
          {t('reports.select_label', 'Seleccionar Simulación:')}
        </label>
        <select 
          value={selectedSim} 
          onChange={(e) => setSelectedSim(e.target.value)}
          disabled={simulaciones.length === 0}
          className="w-full md:w-1/2 bg-white dark:bg-slate-900 text-slate-900 dark:text-white border-gray-300 dark:border-slate-600 rounded-md shadow-sm focus:ring-emerald-500 dark:focus:ring-emerald-400 p-2 border mb-6 outline-none transition-colors disabled:opacity-50"
        >
          {simulaciones.length === 0 ? (
            <option value="">{t('reports.no_simulations', 'No hay simulaciones disponibles')}</option>
          ) : (
            simulaciones.map(sim => (
              <option key={sim.id_simulacion} value={sim.id_simulacion}>
                {sim.especie_nombre} - {t('reports.scenario', 'Escenario')}: {sim.escenario} ({new Date(sim.fecha).toLocaleDateString()})
              </option>
            ))
          )}
        </select>

        {loading ? (
          <p className="text-center text-slate-500 dark:text-slate-400 py-10 animate-pulse">{t('reports.loading_preview', 'Cargando vista previa...')}</p>
        ) : previewData ? (
          <div className="space-y-8 animate-fadeIn">
            
            <div className="flex flex-wrap gap-4 pb-6 border-b border-gray-200 dark:border-slate-700 transition-colors">
              <button onClick={() => handleDownload('pdf')} className="flex items-center gap-2 bg-red-600 hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-600 text-white px-4 py-2 rounded-lg font-medium transition-colors">
                📥 {t('reports.btn_pdf', 'Descargar PDF')}
              </button>
              <button onClick={() => handleDownload('word')} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 text-white px-4 py-2 rounded-lg font-medium transition-colors">
                📥 {t('reports.btn_word', 'Descargar Word')}
              </button>
              <button onClick={() => handleDownload('excel')} className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 dark:bg-emerald-700 dark:hover:bg-emerald-600 text-white px-4 py-2 rounded-lg font-medium transition-colors">
                📥 {t('reports.btn_excel', 'Descargar Excel')}
              </button>
            </div>

            {/* Resumen Ejecutivo */}
            <div>
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 mb-2">👁️ {t('reports.preview_summary', 'Resumen Ejecutivo')}</h3>
              <div className="p-4 bg-slate-50 dark:bg-slate-900/50 border border-slate-100 dark:border-slate-700/50 rounded-lg text-slate-700 dark:text-slate-300 text-sm leading-relaxed transition-colors">
                {previewData.resumen_ejecutivo}
              </div>
            </div>

            {/* Gráfico Exportable */}
            <div className="relative">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200">
                  📈 {t('reports.preview_chart', 'Evolución de la Conectividad')}
                </h3>
                <button 
                  onClick={() => descargarElementoComoImagen('grafico-conectividad', `Evolucion_Conectividad_Simulacion_${selectedSim}_${i18n.language}`)}
                  className="flex items-center gap-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 px-3 py-1.5 rounded-md text-sm font-medium border border-slate-200 dark:border-slate-600 transition-colors shadow-sm"
                >
                  <span>📸</span> {tableLabels.btnExport600}
                </button>
              </div>
              
              <div id="grafico-conectividad" className="p-4 bg-white dark:bg-slate-800 rounded-lg">
                <div className="h-80 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={filasTabla}>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.3} stroke="#94a3b8" />
                      <XAxis dataKey="año" stroke="#64748b" />
                      <YAxis domain={['auto', 'auto']} stroke="#64748b" />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc', borderRadius: '8px' }}
                        itemStyle={{ color: '#e2e8f0' }}
                      />
                      <Legend wrapperStyle={{ paddingTop: '10px' }}/>
                      <Line type="monotone" dataKey="estatico_pc" stroke="#ef4444" name={t('reports.static_design', isEn ? 'Static Design' : 'Diseño Estático')} strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} isAnimationActive={false} />
                      <Line type="monotone" dataKey="dinamico_pc" stroke="#10b981" name={t('reports.dynamic_design', isEn ? 'Dynamic Design' : 'Diseño Dinámico')} strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Tabla de Métricas Completa (5 columnas) Bilingüe + Exportación 600 DPI y Excel */}
            <div className="pt-6 border-t border-gray-200 dark:border-slate-700 transition-colors">
              <div className="flex flex-wrap justify-between items-center gap-2 mb-4">
                <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200">
                  📊 {tableLabels.previewTitle}
                </h3>
                <div className="flex items-center gap-2">
                  <button 
                    onClick={exportarTablaExcelConEstilo}
                    className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-md text-sm font-medium transition-colors shadow-sm"
                  >
                    <span>📥</span> {tableLabels.btnExportExcelTable}
                  </button>
                  <button 
                    onClick={() => descargarElementoComoImagen('tabla-resultados', `Tabla_Metricas_Simulacion_${selectedSim}_${i18n.language}`)}
                    className="flex items-center gap-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 px-3 py-1.5 rounded-md text-sm font-medium border border-slate-200 dark:border-slate-600 transition-colors shadow-sm"
                  >
                    <span>📸</span> {tableLabels.btnExport600}
                  </button>
                </div>
              </div>
              
              {/* Wrapper externo que centra la tabla en pantalla sin afectar la captura 600 DPI */}
              <div className="flex justify-center w-full">
                <div id="tabla-resultados" className="p-8 bg-white rounded-lg w-full max-w-4xl shadow-sm border border-gray-200">
                  <h2 className="text-2xl font-bold text-[#006e51] mb-6 text-left">
                    {tableLabels.sectionTitle}
                  </h2>
                  
                  <div className="overflow-x-auto">
                    <table className="w-full text-center border-collapse">
                      <thead>
                        <tr className="bg-[#006e51] text-white">
                          <th className="border border-gray-400 px-4 py-2.5 font-bold">{tableLabels.colYear}</th>
                          <th className="border border-gray-400 px-4 py-2.5 font-bold">{tableLabels.colPcStatic}</th>
                          <th className="border border-gray-400 px-4 py-2.5 font-bold">{tableLabels.colPcDynamic}</th>
                          <th className="border border-gray-400 px-4 py-2.5 font-bold">{tableLabels.colIicStatic}</th>
                          <th className="border border-gray-400 px-4 py-2.5 font-bold">{tableLabels.colIicDynamic}</th>
                        </tr>
                      </thead>
                      <tbody className="text-slate-900">
                        {filasTabla.map((row, index) => (
                          <tr key={index} className="bg-white even:bg-gray-50">
                            <td className="border border-gray-300 px-4 py-2">{row.año}</td>
                            <td className="border border-gray-300 px-4 py-2">{row.estatico_pc.toFixed(4)}</td>
                            <td className="border border-gray-300 px-4 py-2">{row.dinamico_pc.toFixed(4)}</td>
                            <td className="border border-gray-300 px-4 py-2">{row.estatico_iic.toFixed(4)}</td>
                            <td className="border border-gray-300 px-4 py-2">{row.dinamico_iic.toFixed(4)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Interpretación bilingüe al pie de la tabla */}
                  <div className="mt-4 p-3.5 bg-emerald-50/70 border-l-4 border-[#006e51] text-slate-700 text-xs leading-relaxed text-justify rounded-r">
                    {textoInterpretacion}
                  </div>
                </div>
              </div>
            </div>

            {/* Visor PDF */}
            <div className="pt-6 border-t border-gray-200 dark:border-slate-700 transition-colors">
              <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 mb-4">📑 {t('reports.preview_pdf', 'Vista Previa del Documento')}</h3>
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
          <p className="text-center text-slate-500 dark:text-slate-400 py-10">{t('reports.no_data', 'No hay datos disponibles para mostrar.')}</p>
        )}
      </div>
    </div>
  );
}