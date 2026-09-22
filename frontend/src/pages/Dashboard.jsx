import { useContext, useEffect, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import api from '../services/api';
import { useTranslation } from 'react-i18next';

export default function Dashboard() {
  const { t } = useTranslation();
  const { user } = useContext(AuthContext);
  const [resumen, setResumen] = useState({
    total_especies: 0,
    total_registros: 0,
    total_simulaciones: 0,
    total_usuarios: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchResumen = async () => {
      try {
        const res = await api.get('/datos/resumen');
        if (res.data.success) {
          setResumen(res.data.data);
        }
      } catch (err) {
        console.error("Error obteniendo el resumen del dashboard", err);
      } finally {
        setLoading(false);
      }
    };
    fetchResumen();
  }, []);

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-blue-900 to-blue-600 rounded-xl p-6 text-white shadow-md">
        <h1 className="text-2xl font-bold">{t('dashboard.title', '🌿 Panel Principal - Gemelo Digital')}</h1>
        <p className="mt-2 text-blue-100">
          {t('dashboard.welcome', 'Bienvenido,')} <strong>{user?.nombre_completo}</strong> | {t('dashboard.role', 'Rol:')} {user?.rol}
        </p>
      </div>

      {loading ? (
        <div className="text-center py-10 text-gray-500 animate-pulse">
          {t('dashboard.loading', 'Cargando métricas...')}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 text-center hover:shadow-md transition-shadow">
            <div className="text-3xl font-bold text-blue-900">{resumen.total_especies}</div>
            <div className="text-sm text-gray-500 mt-2">{t('dashboard.species', '🦋 Especies')}</div>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 text-center hover:shadow-md transition-shadow">
            <div className="text-3xl font-bold text-blue-900">{resumen.total_registros.toLocaleString()}</div>
            <div className="text-sm text-gray-500 mt-2">{t('dashboard.records', '📍 Registros de Presencia')}</div>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 text-center hover:shadow-md transition-shadow">
            <div className="text-3xl font-bold text-blue-900">{resumen.total_simulaciones}</div>
            <div className="text-sm text-gray-500 mt-2">{t('dashboard.simulations', '🔬 Simulaciones')}</div>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 text-center hover:shadow-md transition-shadow">
            <div className="text-3xl font-bold text-blue-900">{resumen.total_usuarios}</div>
            <div className="text-sm text-gray-500 mt-2">{t('dashboard.users', '👥 Usuarios Activos')}</div>
          </div>
        </div>
      )}
    </div>
  );
}