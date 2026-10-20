// src/utils/exportarImagen.js
import { toPng } from 'html-to-image';

export const descargarElementoComoImagen = async (elementId, nombreArchivo) => {
  const element = document.getElementById(elementId);

  if (!element) {
    console.error(`No se encontró el elemento con ID: ${elementId}`);
    return;
  }

  // Escala para 600 DPI (600 / 96 = 6.25)
  const scale = 6.25;

  try {
    // toPng soporta oklch, variables CSS modernas y dark mode sin romperse
    const dataUrl = await toPng(element, {
      pixelRatio: scale, 
      backgroundColor: '#ffffff', // Fondo blanco para el artículo
      style: {
        // Previene problemas de desalineación en pantallas con zoom
        transform: 'scale(1)',
        transformOrigin: 'top left'
      }
    });

    // Crear el enlace y forzar la descarga
    const link = document.createElement('a');
    link.download = `${nombreArchivo}_600dpi.png`;
    link.href = dataUrl;
    link.click();
  } catch (err) {
    console.error("Error al exportar la imagen de alta calidad:", err);
  }
};