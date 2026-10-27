import { useState, useContext } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import useDarkMode from '../hooks/useDarkMode';
import { useTranslation } from 'react-i18next';
import ChatBotGemelo from './ChatBotGemelo';
import { Home, Database, Globe, FileText, Users, LogOut, Sun, Moon, Languages, Menu, X } from 'lucide-react';

export default function Layout() {
  const [idSimulacionGlobal, setIdSimulacionGlobal] = useState(null);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { user, logout } = useContext(AuthContext);
  const [theme, toggleTheme] = useDarkMode();
  const { t, i18n } = useTranslation(); 

  const cambiarIdioma = (idioma) => {
    i18n.changeLanguage(idioma);
  };

  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false);
  };

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
    <div className="flex h-screen w-full bg-gray-50 dark:bg-slate-900 overflow-hidden transition-colors duration-200">
      
      {/* Fondo oscuro para móvil cuando el menú está abierto */}
      {isMobileMenuOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black/50 lg:hidden transition-opacity"
          onClick={closeMobileMenu}
        />
      )}

      {/* Sidebar - Oculto en móvil, fijo en escritorio */}
      <aside 
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-slate-800 border-r border-gray-200 dark:border-slate-700 flex flex-col transition-transform duration-300 ease-in-out lg:relative lg:translate-x-0 ${
          isMobileMenuOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full'
        }`}
      >
        <div className="p-6 text-center border-b border-gray-100 dark:border-slate-700 flex justify-between items-center lg:block">
          <div>
            <h2 className="text-xl font-bold text-blue-900 dark:text-blue-400">🌿 Gemelo Digital</h2>
            <p className="text-xs text-gray-500 dark:text-slate-400 mt-1 lg:mx-auto text-left lg:text-center">
              {t('sidebar.subtitle', 'Corredores de Migración')}
            </p>
          </div>
          {/* Botón extra para cerrar el menú desde dentro del sidebar en móviles */}
          <button onClick={closeMobileMenu} className="lg:hidden p-1 text-gray-500 hover:text-gray-800 dark:text-slate-400 dark:hover:text-slate-200">
            <X size={24} />
          </button>
        </div>
        
        <div className="p-4 bg-blue-50 dark:bg-slate-700 mx-4 mt-4 rounded-lg transition-colors">
          <p className="font-semibold text-sm text-gray-800 dark:text-slate-200">{user?.nombre_completo || user?.username}</p>
          <p className="text-xs text-gray-600 dark:text-slate-400 capitalize">
            {t(`roles.${user?.rol?.toLowerCase()}`, user?.rol)}
          </p>
        </div>

        <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
          {visibleMenuItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={closeMobileMenu} // Cierra el menú al navegar en móvil
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
              {theme === 'dark' ? t('sidebar.light_mode', 'Modo Claro') : t('sidebar.dark_mode', 'Modo Oscuro')}
            </span>
          </button>
          
          <button onClick={logout} className="flex w-full items-center px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400 rounded-md hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors">
            <LogOut className="mr-3 h-5 w-5" />
            <span className="ml-2">{t('sidebar.logout', 'Cerrar Sesión')}</span>
          </button>
        </div>
      </aside>

      {/* Contenedor Principal */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden relative">
        
        {/* Navbar superior para móviles (solo visible en pantallas pequeñas) */}
        <div className="lg:hidden flex items-center justify-between p-4 bg-white dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700 z-30 shadow-sm">
          <h1 className="text-xl font-bold text-blue-900 dark:text-blue-400 flex items-center gap-2">
            🌿 Gemelo Digital
          </h1>
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="p-2 rounded-md bg-gray-100 hover:bg-gray-200 dark:bg-slate-700 dark:hover:bg-slate-600 text-gray-700 dark:text-slate-200 transition-colors"
          >
            {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Área de contenido renderizado (Outlet) */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 relative">      
          <Outlet context={setIdSimulacionGlobal} />
          <ChatBotGemelo idSimulacion={idSimulacionGlobal} />
        </main>
      </div>
      
    </div>
  );
}