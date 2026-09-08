export default function Reportes() {
  const handleDownload = (format) => {
    // Aquí se conectará con el endpoint de FastAPI que retorna el archivo
    alert(`Iniciando descarga del reporte en formato: ${format.toUpperCase()}`);
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