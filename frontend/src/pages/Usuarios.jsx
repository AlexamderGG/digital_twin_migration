import { useState, useEffect } from 'react';
import api from '../services/api';

export default function Usuarios() {
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Estados para el Modal CRUD
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    rol: 'Investigador',
    password: '', // Solo se usará al crear
    activo: true
  });

  // 1. LEER (Read) - Cargar usuarios
  const fetchUsuarios = async () => {
    setLoading(true);
    try {
      const res = await api.get('/usuarios');
      // Ajusta esto dependiendo de cómo devuelva los datos tu backend
      const data = res.data.data || res.data;
      setUsuarios(data);
    } catch (err) {
      console.error("Error cargando usuarios", err);
      // Fallback visual temporal si el backend aún no tiene el endpoint
      if (usuarios.length === 0) {
        setUsuarios([
          { id: 1, username: 'admin', email: 'admin@gemelo.com', rol: 'Administrador', activo: true },
          { id: 2, username: 'investigador1', email: 'inv@gemelo.com', rol: 'Investigador', activo: true },
        ]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsuarios();
  }, []);

  // Manejadores del Formulario
  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value
    });
  };

  const openModal = (user = null) => {
    setError('');
    if (user) {
      setEditingUser(user);
      setFormData({
        username: user.username,
        email: user.email,
        rol: user.rol,
        password: '', 
        activo: user.activo
      });
    } else {
      setEditingUser(null);
      setFormData({ username: '', email: '', rol: 'Investigador', password: '', activo: true });
    }
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingUser(null);
  };

  // 2. CREAR Y ACTUALIZAR (Create / Update)
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (editingUser) {
        // Actualizar usuario existente
        // Extraemos password para no enviarlo vacío si no lo cambiaron
        const { password, ...updateData } = formData;
        if (password) updateData.password = password;
        
        await api.put(`/usuarios/${editingUser.id}`, updateData);
      } else {
        // Crear nuevo usuario
        if (!formData.password) {
          setError('La contraseña es obligatoria para nuevos usuarios.');
          setLoading(false);
          return;
        }
        await api.post('/usuarios', formData);
      }
      await fetchUsuarios(); // Recargamos la tabla
      closeModal();
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al guardar el usuario.');
    } finally {
      setLoading(false);
    }
  };

  // 3. ELIMINAR (Delete)
  const handleDelete = async (id) => {
    if (!window.confirm('¿Estás seguro de que deseas eliminar este usuario?')) return;
    
    try {
      await api.delete(`/usuarios/${id}`);
      await fetchUsuarios();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al eliminar el usuario.');
    }
  };

  return (
    <div className="space-y-6 relative">
      {/* Cabecera */}
      <div className="bg-gradient-to-r from-blue-900 to-blue-600 dark:from-slate-800 dark:to-slate-700 rounded-xl p-6 text-white shadow-md transition-colors duration-200">
        <h1 className="text-2xl font-bold">👥 Gestión de Usuarios</h1>
        <p className="mt-2 text-blue-100 dark:text-slate-300">
          Administración de accesos al sistema Gemelo Digital.
        </p>
      </div>

      {/* Panel Principal */}
      <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-gray-100 dark:border-slate-700 transition-colors duration-200">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-lg font-semibold text-gray-800 dark:text-slate-100">Lista de Usuarios</h2>
          <button 
            onClick={() => openModal()}
            className="bg-blue-600 dark:bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-700 dark:hover:bg-blue-600 text-sm font-medium transition-colors"
          >
            + Nuevo Usuario
          </button>
        </div>

        <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-slate-700">
          <table className="w-full text-sm text-left text-gray-500 dark:text-slate-400">
            <thead className="text-xs text-gray-700 dark:text-slate-300 uppercase bg-gray-50 dark:bg-slate-900/50">
              <tr>
                <th className="px-6 py-4 font-semibold">ID</th>
                <th className="px-6 py-4 font-semibold">Usuario</th>
                <th className="px-6 py-4 font-semibold">Email</th>
                <th className="px-6 py-4 font-semibold">Rol</th>
                <th className="px-6 py-4 font-semibold">Estado</th>
                <th className="px-6 py-4 font-semibold text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-6 py-8 text-center text-gray-400 dark:text-slate-500">
                    {loading ? 'Cargando usuarios...' : 'No se encontraron usuarios.'}
                  </td>
                </tr>
              ) : (
                usuarios.map((u) => (
                  <tr key={u.id} className="bg-white dark:bg-slate-800 border-b dark:border-slate-700 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors">
                    <td className="px-6 py-4">{u.id}</td>
                    <td className="px-6 py-4 font-medium text-gray-900 dark:text-slate-100">{u.username}</td>
                    <td className="px-6 py-4">{u.email}</td>
                    <td className="px-6 py-4">
                      <span className="px-3 py-1 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-md text-xs font-medium">
                        {u.rol}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        u.activo 
                          ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' 
                          : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                      }`}>
                        {u.activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right space-x-3">
                      <button onClick={() => openModal(u)} className="text-blue-600 dark:text-blue-400 hover:underline font-medium">Editar</button>
                      <button onClick={() => handleDelete(u.id)} className="text-red-600 dark:text-red-400 hover:underline font-medium">Eliminar</button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal CRUD */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-md overflow-hidden border border-gray-100 dark:border-slate-700">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-slate-700 flex justify-between items-center bg-gray-50 dark:bg-slate-900/50">
              <h3 className="text-lg font-bold text-gray-800 dark:text-slate-100">
                {editingUser ? 'Editar Usuario' : 'Nuevo Usuario'}
              </h3>
              <button onClick={closeModal} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-2xl font-semibold">&times;</button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">Usuario</label>
                <input 
                  type="text" name="username" required
                  value={formData.username} onChange={handleInputChange}
                  className="w-full bg-white dark:bg-slate-900 text-slate-900 dark:text-white border-gray-300 dark:border-slate-600 rounded-md focus:ring-blue-500 focus:border-blue-500 p-2 border outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">Email</label>
                <input 
                  type="email" name="email" required
                  value={formData.email} onChange={handleInputChange}
                  className="w-full bg-white dark:bg-slate-900 text-slate-900 dark:text-white border-gray-300 dark:border-slate-600 rounded-md focus:ring-blue-500 focus:border-blue-500 p-2 border outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  Contraseña {editingUser && <span className="text-xs text-gray-400 font-normal">(Dejar en blanco para mantener actual)</span>}
                </label>
                <input 
                  type="password" name="password" 
                  value={formData.password} onChange={handleInputChange}
                  className="w-full bg-white dark:bg-slate-900 text-slate-900 dark:text-white border-gray-300 dark:border-slate-600 rounded-md focus:ring-blue-500 focus:border-blue-500 p-2 border outline-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">Rol</label>
                  <select 
                    name="rol" value={formData.rol} onChange={handleInputChange}
                    className="w-full bg-white dark:bg-slate-900 text-slate-900 dark:text-white border-gray-300 dark:border-slate-600 rounded-md focus:ring-blue-500 p-2 border outline-none"
                  >
                    <option value="Administrador">Administrador</option>
                    <option value="Investigador">Investigador</option>
                    <option value="Auditor">Auditor</option>
                  </select>
                </div>
                <div className="flex flex-col justify-end pb-2">
                  <label className="flex items-center cursor-pointer">
                    <input 
                      type="checkbox" name="activo" 
                      checked={formData.activo} onChange={handleInputChange}
                      className="w-5 h-5 text-blue-600 rounded border-gray-300 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-900"
                    />
                    <span className="ml-2 text-sm font-medium text-gray-700 dark:text-slate-300">Usuario Activo</span>
                  </label>
                </div>
              </div>

              {error && (
                <div className="mt-2 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded-md border border-red-200 dark:border-red-800">
                  {error}
                </div>
              )}

              <div className="pt-4 flex gap-3">
                <button 
                  type="button" onClick={closeModal}
                  className="flex-1 px-4 py-2 bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-200 rounded-md hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors font-medium"
                >
                  Cancelar
                </button>
                <button 
                  type="submit" disabled={loading}
                  className="flex-1 px-4 py-2 bg-blue-600 dark:bg-blue-500 text-white rounded-md hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors font-medium disabled:opacity-50"
                >
                  {loading ? 'Guardando...' : 'Guardar Usuario'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}