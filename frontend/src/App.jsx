import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useContext } from 'react';
import { AuthProvider, AuthContext } from './context/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Simulacion from './pages/Simulacion';
import Reportes from './pages/ReportesView';
import Usuarios from './pages/Usuarios';
import SpeciesMigrationView from './pages/SpeciesMigrationView';

// 1. Protege las rutas privadas (Si NO hay usuario, manda al login)
const PrivateRoute = ({ children }) => {
  const { user, loading } = useContext(AuthContext);
  
  if (loading) return (
    <div className="h-screen flex items-center justify-center bg-gray-50 dark:bg-slate-900 text-slate-800 dark:text-slate-200 transition-colors">
      Cargando...
    </div>
  );
  
  return user ? children : <Navigate to="/login" replace />;
};

// 2. Protege el Login (Si YA hay usuario, manda al inicio)
const PublicRoute = ({ children }) => {
  const { user, loading } = useContext(AuthContext);
  
  if (loading) return null;
  
  return user ? <Navigate to="/" replace /> : children;
};

// 3. Protege las rutas de Administrador (Si NO es admin, lo devuelve al inicio)
const AdminRoute = ({ children }) => {
  const { user } = useContext(AuthContext);
  
  if (user?.rol?.toLowerCase() !== 'administrador') {
    return <Navigate to="/" replace />;
  }
  
  return children;
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
            <Route path="simulacion" element={<Simulacion />} />
            <Route path="species-migration" element={<SpeciesMigrationView />} />
            <Route path="reportes" element={<Reportes />} />
            
            {/* Ruta restringida: Solo Administradores */}
            <Route 
              path="usuarios" 
              element={
                <AdminRoute>
                  <Usuarios />
                </AdminRoute>
              } 
            />
          </Route>

          {/* Ruta comodín (404): Si escribe cualquier URL inválida, lo regresa a la raíz */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;