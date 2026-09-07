"""
Módulo de Autenticación y Gestión de Usuarios
Gemelo Digital de Corredores de Migración

Implementa:
- Login/logout con hash bcrypt
- Gestión de roles y permisos
- Verificación de acceso por módulo
- CRUD completo de usuarios
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

import bcrypt
import jwt
from sqlalchemy import text

from config import Config, DatabaseConnection

logger = logging.getLogger(__name__)


@dataclass
class UserSession:
    """Datos de sesión de usuario autenticado"""
    id_usuario: int
    username: str
    email: str
    nombre_completo: str
    id_rol: int
    nombre_rol: str
    permisos: Dict[str, Any]
    institucion: Optional[str] = None
    token: Optional[str] = None


class AuthManager:
    """Gestor principal de autenticación y autorización"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Genera hash bcrypt de una contraseña"""
        return bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verifica una contraseña contra su hash"""
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                password_hash.encode('utf-8')
            )
        except Exception:
            return False
    
    @staticmethod
    def create_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Crea un token JWT"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, Config.SECRET_KEY, algorithm=Config.JWT_ALGORITHM)
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """Decodifica y valida un token JWT"""
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expirado")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token inválido: {e}")
            return None
    
    @classmethod
    def login(cls, username: str, password: str) -> Optional[UserSession]:
        """Autentica un usuario y retorna su sesión"""
        try:
            query = """
                SELECT u.id_usuario, u.username, u.email, u.nombre_completo,
                       u.password_hash, u.id_rol, u.institucion, u.activo,
                       r.nombre_rol, r.permisos
                FROM usuarios u
                JOIN roles r ON u.id_rol = r.id_rol
                WHERE u.username = :username OR u.email = :username
            """
            results = DatabaseConnection.execute_query(query, {"username": username})
            
            if not results:
                logger.warning(f"Intento de login fallido: usuario '{username}' no encontrado")
                return None
            
            user = results[0]
            
            if not user['activo']:
                logger.warning(f"Usuario '{username}' desactivado")
                return None
            
            if not cls.verify_password(password, user['password_hash']):
                logger.warning(f"Contraseña incorrecta para usuario '{username}'")
                return None
            
            # Actualizar último acceso
            update_query = """
                UPDATE usuarios SET ultimo_acceso = CURRENT_TIMESTAMP
                WHERE id_usuario = :id_usuario
            """
            DatabaseConnection.execute_non_query(update_query, {"id_usuario": user['id_usuario']})
            
            # Crear token
            token_data = {
                "sub": user['username'],
                "id_usuario": user['id_usuario'],
                "id_rol": user['id_rol']
            }
            token = cls.create_token(token_data)
            
            session = UserSession(
                id_usuario=user['id_usuario'],
                username=user['username'],
                email=user['email'],
                nombre_completo=user['nombre_completo'],
                id_rol=user['id_rol'],
                nombre_rol=user['nombre_rol'],
                permisos=user['permisos'] or {},
                institucion=user['institucion'],
                token=token
            )
            
            logger.info(f"Login exitoso: {user['username']} (Rol: {user['nombre_rol']})")
            return session
            
        except Exception as e:
            logger.error(f"Error en login: {e}")
            return None
    
    @staticmethod
    def has_permission(permisos: Dict[str, Any], modulo: str, accion: str) -> bool:
        """Verifica si un usuario tiene permiso para una acción en un módulo"""
        try:
            return bool(permisos.get(modulo, {}).get(accion, False))
        except Exception:
            return False
    
    @staticmethod
    def get_all_roles() -> List[Dict[str, Any]]:
        """Obtiene todos los roles del sistema"""
        query = """
            SELECT id_rol, nombre_rol, descripcion, permisos, activo
            FROM roles
            WHERE activo = TRUE
            ORDER BY id_rol
        """
        return DatabaseConnection.execute_query(query)
    
    @staticmethod
    def get_all_users(include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Obtiene lista de usuarios"""
        query = """
            SELECT u.id_usuario, u.username, u.email, u.nombre_completo,
                   u.institucion, u.telefono, u.id_rol, r.nombre_rol,
                   u.fecha_creacion, u.ultimo_acceso, u.activo
            FROM usuarios u
            JOIN roles r ON u.id_rol = r.id_rol
            WHERE (:include_inactive = TRUE OR u.activo = TRUE)
            ORDER BY u.nombre_completo
        """
        return DatabaseConnection.execute_query(query, {"include_inactive": include_inactive})
    
    @staticmethod
    def create_user(username: str, email: str, nombre_completo: str,
                    password: str, id_rol: int, institucion: str = None,
                    telefono: str = None) -> Dict[str, Any]:
        """Crea un nuevo usuario"""
        password_hash = AuthManager.hash_password(password)
        
        query = """
            INSERT INTO usuarios 
            (username, email, nombre_completo, password_hash, id_rol, institucion, telefono)
            VALUES (:username, :email, :nombre_completo, :password_hash, :id_rol, 
                    :institucion, :telefono)
            RETURNING id_usuario, username, email, nombre_completo, id_rol
        """
        results = DatabaseConnection.execute_query(query, {
            "username": username,
            "email": email,
            "nombre_completo": nombre_completo,
            "password_hash": password_hash,
            "id_rol": id_rol,
            "institucion": institucion,
            "telefono": telefono
        })
        
        if results:
            logger.info(f"Usuario creado: {username}")
            return {"success": True, "user": results[0]}
        return {"success": False, "error": "No se pudo crear el usuario"}
    
    @staticmethod
    def update_user(id_usuario: int, **kwargs) -> Dict[str, Any]:
        """Actualiza datos de un usuario"""
        allowed_fields = ['email', 'nombre_completo', 'id_rol', 'institucion', 
                         'telefono', 'activo']
        
        # Si hay contraseña nueva, hashearla
        if 'password' in kwargs and kwargs['password']:
            kwargs['password_hash'] = AuthManager.hash_password(kwargs['password'])
            del kwargs['password']
        
        # Filtrar campos permitidos
        update_data = {k: v for k, v in kwargs.items() if k in allowed_fields or k == 'password_hash'}
        
        if not update_data:
            return {"success": False, "error": "No hay campos para actualizar"}
        
        set_clause = ", ".join([f"{k} = :{k}" for k in update_data.keys()])
        update_data['id_usuario'] = id_usuario
        
        query = f"""
            UPDATE usuarios SET {set_clause}
            WHERE id_usuario = :id_usuario
            RETURNING id_usuario, username, email, nombre_completo
        """
        
        results = DatabaseConnection.execute_query(query, update_data)
        if results:
            logger.info(f"Usuario actualizado: ID {id_usuario}")
            return {"success": True, "user": results[0]}
        return {"success": False, "error": "Usuario no encontrado"}
    
    @staticmethod
    def delete_user(id_usuario: int) -> Dict[str, Any]:
        """Desactiva un usuario (soft delete)"""
        query = """
            UPDATE usuarios SET activo = FALSE
            WHERE id_usuario = :id_usuario
            RETURNING id_usuario, username
        """
        results = DatabaseConnection.execute_query(query, {"id_usuario": id_usuario})
        if results:
            logger.info(f"Usuario desactivado: ID {id_usuario}")
            return {"success": True, "user": results[0]}
        return {"success": False, "error": "Usuario no encontrado"}
    
    @staticmethod
    def change_password(id_usuario: int, old_password: str, new_password: str) -> Dict[str, Any]:
        """Cambia la contraseña de un usuario"""
        # Obtener hash actual
        query = "SELECT password_hash FROM usuarios WHERE id_usuario = :id_usuario"
        results = DatabaseConnection.execute_query(query, {"id_usuario": id_usuario})
        
        if not results:
            return {"success": False, "error": "Usuario no encontrado"}
        
        current_hash = results[0]['password_hash']
        
        if not AuthManager.verify_password(old_password, current_hash):
            return {"success": False, "error": "Contraseña actual incorrecta"}
        
        # Actualizar
        new_hash = AuthManager.hash_password(new_password)
        update_query = """
            UPDATE usuarios SET password_hash = :new_hash
            WHERE id_usuario = :id_usuario
        """
        DatabaseConnection.execute_non_query(update_query, {
            "new_hash": new_hash,
            "id_usuario": id_usuario
        })
        
        logger.info(f"Contraseña cambiada para usuario ID {id_usuario}")
        return {"success": True, "message": "Contraseña actualizada exitosamente"}


# --- Funciones de utilidad para Streamlit ---
def get_current_user(st) -> Optional[UserSession]:
    """Obtiene el usuario actual de la sesión Streamlit"""
    if 'user_session' in st.session_state:
        return st.session_state['user_session']
    return None


def require_login(st) -> Optional[UserSession]:
    """Requiere que el usuario esté autenticado, redirige a login si no lo está"""
    user = get_current_user(st)
    if user is None:
        st.warning("Por favor, inicie sesión para acceder a esta sección.")
        st.stop()
    return user


def require_permission(st, modulo: str, accion: str) -> bool:
    """Verifica permiso y muestra mensaje si no lo tiene"""
    user = get_current_user(st)
    if user is None:
        require_login(st)
        return False
    
    if not AuthManager.has_permission(user.permisos, modulo, accion):
        st.error(f"No tiene permisos suficientes para: {modulo} > {accion}")
        st.stop()
        return False
    return True
