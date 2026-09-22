
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import esTranslation from './locales/es/translation.json';
import enTranslation from './locales/en/translation.json';

i18n
  .use(initReactI18next)
  .init({
    resources: {
      es: { translation: esTranslation },
      en: { translation: enTranslation }
    },
    lng: 'es', // Idioma por defecto al abrir la app
    fallbackLng: 'es', // Si falta una traducción en inglés, mostrará español
    interpolation: {
      escapeValue: false 
    }
  });

export default i18n;