import { useContext } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import useDarkMode from '../hooks/useDarkMode';
import { useTranslation } from 'react-i18next';
import { Home, Database, Globe, FileText, Users, LogOut, Sun, Moon, Languages } from 'lucide-react';

export default function Layout() {
  const { user, logout } = useContext(AuthContext);
  const [theme, toggleTheme] = useDarkMode();
  const { t, i18n } = useTranslation(); 

  const cambiarIdioma = (idioma) => {
    i18n.changeLanguage(idioma);
  };

  // 1. Aplicamos t() a los nombres del menú
  const menuItems = [
    { name: t('sidebar.main_panel', 'Panel Principal'), icon: Home, path: '/' },
    { name: t('sidebar.scenarios', 'Simulación Escenarios'), icon: Globe, path: '/simulacion' },
    { name: t('sidebar.migration', 'Migración Especie'), icon: Database, path: '/species-migration' },
    { name: t('sidebar.reports', 'Reportes'), icon: FileText, path: '/reportes' },
    { name: t('sidebar.users', 'Gestión Usuarios'), icon: Users, path: '/usuarios', adminOnly: true },
  ];

  const visibleMenuItems = menuItems.filter(item => 
    !item.adminOnly || user?.rol?.toLowerCase() === 'administrador'
  );

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-slate-900 transition-colors duration-200">
      
      <aside className="w-64 bg-white dark:bg-slate-800 border-r border-gray-200 dark:border-slate-700 flex flex-col transition-colors duration-200">
        <div className="p-6 text-center border-b border-gray-100 dark:border-slate-700">
          <h2 className="text-xl font-bold text-blue-900 dark:text-blue-400">🌿 Gemelo Digital</h2>
          {/* Traducimos el subtítulo del sistema */}
          <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{t('sidebar.subtitle', 'Corredores de Migración')}</p>
        </div>
        
        <div className="p-4 bg-blue-50 dark:bg-slate-700 mx-4 mt-4 rounded-lg transition-colors">
          <p className="font-semibold text-sm text-gray-800 dark:text-slate-200">{user?.nombre_completo || user?.username}</p>
          {/* Traducimos el rol dinámicamente usando una función traductora para los roles */}
          <p className="text-xs text-gray-600 dark:text-slate-400 capitalize">
            {t(`roles.${user?.rol?.toLowerCase()}`, user?.rol)}
          </p>
        </div>

        <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
          {visibleMenuItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path} // Cambiado a item.path para evitar problemas con la traducción dinámica
                to={item.path}
                className={({ isActive }) =>
                  isActive 
                    ? 'flex items-center px-3 py-2.5 text-sm font-medium rounded-md transition-colors bg-blue-600 text-white dark:bg-blue-500' 
                    : 'flex items-center px-3 py-2.5 text-sm font-medium rounded-md transition-colors text-gray-700 dark:text-slate-300 hover:bg-blue-50 dark:hover:bg-slate-700 hover:text-blue-700 dark:hover:text-blue-400'
                }
              >
                <Icon className="mr-3 h-5 w-5" />
                {item.name}
              </NavLink>
            );
          })}
        </nav>

        <div className="p-4 border-t border-gray-200 dark:border-slate-700 space-y-2">
          
          <div className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium text-slate-700 dark:text-slate-300">
            <div className="flex items-center">
              <Languages className="mr-3 h-5 w-5 opacity-70" />
              {/* 2. Usamos t() en lugar del condicional manual */}
              <span>{t('sidebar.language', 'Idioma')}</span>
            </div>
            <div className="flex gap-1 bg-gray-100 dark:bg-slate-900 p-1 rounded-md border border-gray-200 dark:border-slate-700">
              <button onClick={() => cambiarIdioma('es')} className={i18n.language === 'es' ? 'px-2 py-1 rounded text-xs font-bold transition-all bg-white dark:bg-slate-700 shadow-sm text-blue-600 dark:text-blue-400' : 'px-2 py-1 rounded text-xs font-bold transition-all text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}>ES</button>
              <button onClick={() => cambiarIdioma('en')} className={i18n.language === 'en' ? 'px-2 py-1 rounded text-xs font-bold transition-all bg-white dark:bg-slate-700 shadow-sm text-blue-600 dark:text-blue-400' : 'px-2 py-1 rounded text-xs font-bold transition-all text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}>EN</button>
            </div>
          </div>

          <button onClick={toggleTheme} className="flex w-full items-center px-3 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">
            {theme === 'dark' ? <Sun className="mr-3 h-5 w-5 text-amber-500" /> : <Moon className="mr-3 h-5 w-5 text-indigo-400" />}
            <span className="ml-2">
              {/* 3. Usamos t() para los modos claro/oscuro */}
              {theme === 'dark' ? t('sidebar.light_mode', 'Modo Claro') : t('sidebar.dark_mode', 'Modo Oscuro')}
            </span>
          </button>
          
          <button onClick={logout} className="flex w-full items-center px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400 rounded-md hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors">
            <LogOut className="mr-3 h-5 w-5" />
            <span className="ml-2">{t('sidebar.logout', 'Cerrar Sesión')}</span>
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}