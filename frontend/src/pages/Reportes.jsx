import React, { useState } from 'react';
import api from '../services/api';

export default function Reportes() {
  const [loading, setLoading] = useState(false);

  // Función genérica para descargar cualquier formato
  const handleDownload = async (formato) => {
    setLoading(true);
    try {
      // Es crucial poner responseType: 'blob' para que Axios no intente leerlo como JSON
      const response = await api.get(`/reportes/${formato}`, {
        responseType: 'blob' 
      });

      // Creamos un link temporal en memoria con el archivo
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('link');
      link.href = url;
      
      // Extraemos el nombre del archivo de los headers si es posible, o forzamos uno
      const extension = formato === 'excel' ? 'xlsx' : formato === 'word' ? 'docx' : 'pdf';
      link.setAttribute('download', `Resultados_Migracion.${extension}`);
      
      // Simulamos el clic y limpiamos la memoria
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

    } catch (error) {
      console.error(`Error descargando el reporte ${formato}:`, error);
      alert("Hubo un problema al generar el reporte. Verifica que existan simulaciones previas.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-blue-900 to-blue-600 rounded-xl p-6 text-white shadow-md">
        <h1 className="text-2xl font-bold">📄 Generación de Reportes</h1>
        <p className="mt-2 text-blue-100">
          Exportación de resultados en formatos PDF, Word y Excel.
        </p>
      </div>

      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Descargar Resultados de Simulación</h2>
        <div className="flex space-x-4">
          <button 
            onClick={() => handleDownload('pdf')}
            className="flex-1 bg-red-50 text-red-600 border border-red-200 font-medium py-3 px-4 rounded-md hover:bg-red-100 transition"
          >
            📥 Descargar PDF
          </button>
          <button 
            onClick={() => handleDownload('docx')}
            className="flex-1 bg-blue-50 text-blue-600 border border-blue-200 font-medium py-3 px-4 rounded-md hover:bg-blue-100 transition"
          >
            📥 Descargar Word
          </button>
          <button 
            onClick={() => handleDownload('xlsx')}
            className="flex-1 bg-green-50 text-green-600 border border-green-200 font-medium py-3 px-4 rounded-md hover:bg-green-100 transition"
          >
            📥 Descargar Excel
          </button>
        </div>
      </div>
    </div>
  );
}