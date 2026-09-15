import { useContext } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { 
  Home, 
  Database, 
  Cpu, 
  Zap, 
  Globe, 
  FileText, 
  Users, 
  LogOut 
} from 'lucide-react';

export default function Layout() {
  const { user, logout } = useContext(AuthContext);

  const menuItems = [
    { name: 'Panel Principal', icon: Home, path: '/' },
    { name: 'Idoneidad de Hábitat', icon: Cpu, path: '/modelos' }, // Cambiamos el nombre
    { name: 'Conectividad', icon: Zap, path: '/conectividad' },
    { name: 'Simulación Escenarios', icon: Globe, path: '/simulacion' },
    { name: 'Migración Especie', icon: Database, path: '/species-migration' },
    { name: 'Reportes', icon: FileText, path: '/reportes' },
    { name: 'Gestión Usuarios', icon: Users, path: '/usuarios' },
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Menú Lateral */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 text-center border-b border-gray-100">
          <h2 className="text-xl font-bold text-blue-900">🌿 Gemelo Digital</h2>
          <p className="text-xs text-gray-500 mt-1">Corredores de Migración</p>
        </div>
        
        <div className="p-4 bg-blue-50 mx-4 mt-4 rounded-lg">
          <p className="font-semibold text-sm text-gray-800">{user?.nombre_completo}</p>
          <p className="text-xs text-gray-600 capitalize">{user?.rol}</p>
        </div>

        <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
          {menuItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center px-3 py-2.5 text-sm font-medium rounded-md transition-colors ${
                  isActive 
                    ? 'bg-blue-600 text-white' 
                    : 'text-gray-700 hover:bg-blue-50 hover:text-blue-700'
                }`
              }
            >
              <item.icon className="mr-3 h-5 w-5" />
              {item.name}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-gray-200">
          <button
            onClick={logout}
            className="flex w-full items-center px-3 py-2 text-sm font-medium text-red-600 rounded-md hover:bg-red-50 transition-colors"
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