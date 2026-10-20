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
    const width = element.offsetWidth;
    const height = element.offsetHeight;

    const dataUrl = await toPng(element, {
      pixelRatio: scale,
      width: width,
      height: height,
      backgroundColor: '#ffffff',
      style: {
        margin: '0', 
        transform: 'none'
      }
    });

    const link = document.createElement('a');
    link.download = `${nombreArchivo}_600dpi.png`;
    link.href = dataUrl;
    link.click();
  } catch (err) {
    console.error("Error al exportar la imagen de alta calidad:", err);
  }
};