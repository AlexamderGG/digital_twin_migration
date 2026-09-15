import { useContext } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import useDarkMode from '../hooks/useDarkMode';
import { 
  Home, 
  Database, 
  Cpu, 
  Zap, 
  Globe, 
  FileText, 
  Users, 
  LogOut,
  Sun,  
  Moon  
} from 'lucide-react';

export default function Layout() {
  const { user, logout } = useContext(AuthContext);
  // Inicializamos el hook del modo oscuro
  const [theme, toggleTheme] = useDarkMode();

  const menuItems = [
    { name: 'Panel Principal', icon: Home, path: '/' },
    { name: 'Idoneidad de Hábitat', icon: Cpu, path: '/modelos' },
    { name: 'Conectividad', icon: Zap, path: '/conectividad' },
    { name: 'Simulación Escenarios', icon: Globe, path: '/simulacion' },
    { name: 'Migración Especie', icon: Database, path: '/species-migration' },
    { name: 'Reportes', icon: FileText, path: '/reportes' },
    { name: 'Gestión Usuarios', icon: Users, path: '/usuarios' },
  ];

  return (
    // Agregamos dark:bg-slate-900 al fondo global
    <div className="flex h-screen bg-gray-50 dark:bg-slate-900 transition-colors duration-200">
      
      {/* Menú Lateral con clases dark: */}
      <aside className="w-64 bg-white dark:bg-slate-800 border-r border-gray-200 dark:border-slate-700 flex flex-col transition-colors duration-200">
        <div className="p-6 text-center border-b border-gray-100 dark:border-slate-700">
          <h2 className="text-xl font-bold text-blue-900 dark:text-blue-400">🌿 Gemelo Digital</h2>
          <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">Corredores de Migración</p>
        </div>
        
        <div className="p-4 bg-blue-50 dark:bg-slate-700 mx-4 mt-4 rounded-lg transition-colors">
          <p className="font-semibold text-sm text-gray-800 dark:text-slate-200">{user?.nombre_completo}</p>
          <p className="text-xs text-gray-600 dark:text-slate-400 capitalize">{user?.rol}</p>
        </div>

        <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
          {menuItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center px-3 py-2.5 text-sm font-medium rounded-md transition-colors ${
                  isActive 
                    ? 'bg-blue-600 text-white dark:bg-blue-500' 
                    : 'text-gray-700 dark:text-slate-300 hover:bg-blue-50 dark:hover:bg-slate-700 hover:text-blue-700 dark:hover:text-blue-400'
                }`
              }
            >
              <item.icon className="mr-3 h-5 w-5" />
              {item.name}
            </NavLink>
          ))}
        </nav>

        {/* Zona inferior: Botón Tema + Botón Logout */}
        <div className="p-4 border-t border-gray-200 dark:border-slate-700 space-y-2">
          
          {/* Botón para alternar Modo Oscuro */}
          <button
            onClick={toggleTheme}
            className="flex w-full items-center px-3 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          >
            {theme === 'dark' ? (
              <>
                <Sun className="mr-3 h-5 w-5 text-amber-500" />
                Modo Claro
              </>
            ) : (
              <>
                <Moon className="mr-3 h-5 w-5 text-indigo-400" />
                Modo Oscuro
              </>
            )}
          </button>
          {/* Botón Cerrar Sesión */}
          <button
            onClick={logout}
            className="flex w-full items-center px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400 rounded-md hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors"
          >
            <LogOut className="mr-3 h-5 w-5" />
            Cerrar Sesión
          </button>
        </div>
      </aside>

      {/* Contenido Principal */}
      <main className="flex-1 overflow-y-auto p-8">
        <Outlet /> {/* Aquí se renderizarán las páginas hijas */}
      </main>
    </div>
  );
}