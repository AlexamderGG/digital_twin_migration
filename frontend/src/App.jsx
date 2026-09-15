import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useContext } from 'react';
import { AuthProvider, AuthContext } from './context/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ModelosHabitat from './pages/ModelosHabitat';
import Simulacion from './pages/Simulacion';
import Conectividad from './pages/Conectividad';
import Reportes from './pages/ReportesView';
import Usuarios from './pages/Usuarios';
import SpeciesMigrationView from './pages/SpeciesMigrationView';

// 1. Protege las rutas privadas (Si NO hay usuario, manda al login)
const PrivateRoute = ({ children }) => {
  const { user, loading } = useContext(AuthContext);
  
  if (loading) return (
    // Agregamos dark mode a la pantalla de carga para evitar pantallazos blancos
    <div className="h-screen flex items-center justify-center bg-gray-50 dark:bg-slate-900 text-slate-800 dark:text-slate-200 transition-colors">
      Cargando...
    </div>
  );
  
  // replace={true} evita que el usuario pueda usar el botón "Atrás" para volver a la ruta bloqueada
  return user ? children : <Navigate to="/login" replace />;
};

// 2. Protege el Login (Si YA hay usuario, manda al inicio)
const PublicRoute = ({ children }) => {
  const { user, loading } = useContext(AuthContext);
  
  if (loading) return null;
  
  return user ? <Navigate to="/" replace /> : children;
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Ruta pública: Login */}
          <Route 
            path="/login" 
            element={
              <PublicRoute>
                <Login />
              </PublicRoute>
            } 
          />
          
          {/* Rutas privadas: Envueltas en el Layout */}
          <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="modelos" element={<ModelosHabitat />} />
            <Route path="simulacion" element={<Simulacion />} />
            <Route path="species-migration" element={<SpeciesMigrationView />} />
            <Route path="conectividad" element={<Conectividad />} />
            <Route path="reportes" element={<Reportes />} />
            <Route path="usuarios" element={<Usuarios />} />
          </Route>

          {/* Ruta comodín (404): Si escribe cualquier URL inválida, lo regresa a la raíz */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;