import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocation } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export default function ChatBotGemelo({ idSimulacion = null }) {
  const { t } = useTranslation();
  const location = useLocation();
  
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false); // <-- NUEVO ESTADO PARA AGRANDAR
  const [mensaje, setMensaje] = useState("");
  const [conversacion, setConversacion] = useState([]);
  const [cargando, setCargando] = useState(false);
  const mensajesEndRef = useRef(null);

  useEffect(() => {
    mensajesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversacion, cargando]);

  const enviarMensaje = async () => {
    if (!mensaje.trim()) return;

    const nuevosMensajes = [...conversacion, { rol: "user", texto: mensaje }];
    setConversacion(nuevosMensajes);
    setMensaje("");
    setCargando(true);

    try {
      const token = localStorage.getItem('token'); 
      
      const bodyData = {
        mensaje: mensaje,
        pantalla: location.pathname,
        id_simulacion: idSimulacion ? Number(idSimulacion) : null
      };

      const response = await fetch("http://localhost:8000/api/reportes/chat_unificado", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` 
        },
        body: JSON.stringify(bodyData)
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setConversacion([...nuevosMensajes, { rol: "ai", texto: data.respuesta }]);
      } else {
        setConversacion([...nuevosMensajes, { rol: "error", texto: t('chat.error_api') }]);
      }
    } catch (error) {
      setConversacion([...nuevosMensajes, { rol: "error", texto: t('chat.error_network') }]);
    } finally {
      setCargando(false);
    }
  };

  const getContextName = () => {
    if (location.pathname.includes('reportes')) return 'Reportes y Métricas';
    if (location.pathname.includes('usuarios')) return 'Gestión de Usuarios';
    if (location.pathname.includes('simulacion')) return 'Simulación de Escenarios';
    if (location.pathname.includes('species')) return 'Migración de Especies';
    return 'Panel Principal';
  };

  const markdownComponents = {
    p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
    ul: ({node, ...props}) => <ul className="list-disc ml-5 mb-2 space-y-1" {...props} />,
    ol: ({node, ...props}) => <ol className="list-decimal ml-5 mb-2 space-y-1" {...props} />,
    li: ({node, ...props}) => <li className="leading-relaxed" {...props} />,
    strong: ({node, ...props}) => <strong className="font-bold text-emerald-700 dark:text-emerald-400" {...props} />,
    table: ({node, ...props}) => (
      <div className="overflow-x-auto my-2">
        <table className="w-full text-left border-collapse text-sm" {...props} />
      </div>
    ),
    th: ({node, ...props}) => <th className="border-b border-gray-300 dark:border-slate-600 px-2 py-1 bg-gray-200 dark:bg-slate-800 font-semibold" {...props} />,
    td: ({node, ...props}) => <td className="border-b border-gray-200 dark:border-slate-700 px-2 py-1" {...props} />,
    a: ({node, ...props}) => <a className="text-blue-500 hover:underline" target="_blank" rel="noopener noreferrer" {...props} />,
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 font-sans">
      {isOpen && (
        <div 
          // LA CLASE DINÁMICA: Cambia el ancho y el alto dependiendo de si está expandido
          className={`bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border border-gray-200 dark:border-slate-700 flex flex-col overflow-hidden mb-4 transition-all duration-300 ease-in-out origin-bottom-right ${
            isExpanded ? 'w-[90vw] sm:w-[80vw] md:w-[800px] h-[80vh]' : 'w-80 sm:w-96 md:w-[28rem] h-[520px]'
          }`}
        >
          
          <div className="bg-emerald-700 dark:bg-emerald-800 text-white p-4 flex justify-between items-center shadow-md">
            <div>
              <h3 className="font-bold text-lg">{t('chat.title', 'Asistente Ecológico')}</h3>
              <p className="text-emerald-100 text-xs">
                📍 Viendo: {getContextName()}
              </p>
            </div>
            
            {/* BOTONES DE CABECERA */}
            <div className="flex items-center gap-2">
              <button 
                onClick={() => setIsExpanded(!isExpanded)} 
                className="hover:bg-emerald-600 dark:hover:bg-emerald-700 p-1.5 rounded-full transition-colors"
                title={isExpanded ? "Reducir tamaño" : "Ampliar tamaño"}
              >
                {isExpanded ? (
                  // Ícono de minimizar
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 14h6m0 0v6m0-6l-7 7m17-11h-6m0 0V4m0 6l7-7M4 10h6m0 0V4m0 6l-7-7m17 11h-6m0 0v6m0-6l7 7"></path></svg>
                ) : (
                  // Ícono de maximizar
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"></path></svg>
                )}
              </button>
              
              <button 
                onClick={() => { setIsOpen(false); setIsExpanded(false); }} 
                className="hover:bg-emerald-600 dark:hover:bg-emerald-700 p-1.5 rounded-full transition-colors"
                title="Cerrar"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"></path></svg>
              </button>
            </div>
          </div>

          <div className="flex-1 p-4 overflow-y-auto bg-gray-50 dark:bg-slate-900 space-y-4">
            {conversacion.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.rol === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] p-3 rounded-2xl text-sm ${
                  msg.rol === "user" 
                    ? "bg-emerald-600 text-white rounded-br-none shadow-sm" 
                    : msg.rol === "error" 
                      ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-bl-none border border-red-200 dark:border-red-800/50" 
                      : "bg-white dark:bg-slate-700 text-gray-800 dark:text-slate-200 rounded-bl-none shadow-sm border border-gray-100 dark:border-slate-600"
                }`}>
                  {msg.rol === "ai" ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                      {msg.texto}
                    </ReactMarkdown>
                  ) : (
                    <span>{msg.texto}</span>
                  )}
                </div>
              </div>
            ))}
            {cargando && (
              <div className="flex justify-start">
                <div className="bg-white dark:bg-slate-700 p-3 rounded-2xl rounded-bl-none shadow-sm flex space-x-2 items-center border border-gray-100 dark:border-slate-600">
                  <div className="w-2 h-2 bg-gray-400 dark:bg-slate-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 dark:bg-slate-400 rounded-full animate-bounce delay-75"></div>
                  <div className="w-2 h-2 bg-gray-400 dark:bg-slate-400 rounded-full animate-bounce delay-150"></div>
                </div>
              </div>
            )}
            <div ref={mensajesEndRef} />
          </div>

          <div className="p-3 bg-white dark:bg-slate-800 border-t border-gray-200 dark:border-slate-700 flex items-center gap-2">
            <input 
              type="text" 
              value={mensaje}
              onChange={(e) => setMensaje(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && enviarMensaje()}
              className="flex-1 bg-gray-100 dark:bg-slate-900 border-transparent rounded-full px-4 py-2 text-sm text-gray-800 dark:text-slate-200 focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              placeholder={t('chat.placeholder', 'Escribe tu pregunta...')}
              disabled={cargando}
            />
            <button 
              onClick={enviarMensaje} 
              disabled={!mensaje.trim() || cargando}
              className="bg-emerald-600 text-white p-2 rounded-full hover:bg-emerald-700 disabled:opacity-50 transition-colors flex-shrink-0"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg>
            </button>
          </div>
        </div>
      )}

      {!isOpen && (
        <button onClick={() => setIsOpen(true)} className="bg-emerald-600 text-white p-4 rounded-full shadow-2xl hover:bg-emerald-700 hover:scale-110 transition-all duration-300 border-2 border-white dark:border-slate-800">
          <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"></path></svg>
        </button>
      )}
    </div>
  );
}