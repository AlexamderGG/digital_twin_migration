from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from passlib.context import CryptContext
from config import DatabaseConnection
from routers.auth import get_current_user_api

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password[:72])

class UsuarioCreate(BaseModel):
    username: str
    email: str
    password: str
    rol: str = "Investigador"
    activo: bool = True

class UsuarioUpdate(BaseModel):
    username: str
    email: str
    password: Optional[str] = None
    rol: str
    activo: bool


@router.get("/")
def obtener_usuarios(current_user: dict = Depends(get_current_user_api)):
    try:
        query = """
            SELECT id_usuario as id, username, email, rol, activo 
            FROM usuarios 
            ORDER BY id_usuario DESC
        """
        usuarios = DatabaseConnection.execute_query(query)
        
        return {
            "success": True,
            "data": usuarios if usuarios else []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
def crear_usuario(user: UsuarioCreate, current_user: dict = Depends(get_current_user_api)):
    try:
        check_query = "SELECT id_usuario FROM usuarios WHERE username = :user OR email = :email"
        existente = DatabaseConnection.execute_query(check_query, {"user": user.username, "email": user.email})
        
        if existente:
            raise HTTPException(status_code=400, detail="El nombre de usuario o correo electrónico ya está registrado.")
            
        hashed_password = get_password_hash(user.password)
        
        insert_query = """
            INSERT INTO usuarios (username, email, password_hash, rol, activo, fecha_creacion)
            VALUES (:username, :email, :password_hash, :rol, :activo, CURRENT_TIMESTAMP)
        """
        params = {
            "username": user.username,
            "email": user.email,
            "password_hash": hashed_password,
            "rol": user.rol,
            "activo": user.activo
        }
        
        DatabaseConnection.execute_non_query(insert_query, params)
        return {"success": True, "message": "Usuario creado exitosamente"}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear usuario: {str(e)}")

@router.put("/{id_usuario}")
def actualizar_usuario(id_usuario: int, user: UsuarioUpdate, current_user: dict = Depends(get_current_user_api)):
    try:
        check_query = "SELECT id_usuario FROM usuarios WHERE id_usuario = :id"
        if not DatabaseConnection.execute_query(check_query, {"id": id_usuario}):
            raise HTTPException(status_code=404, detail="Usuario no encontrado.")

        if user.password:
            update_query = """
                UPDATE usuarios 
                SET username = :username, email = :email, rol = :rol, 
                    activo = :activo, password_hash = :password_hash
                WHERE id_usuario = :id_usuario
            """
            params = {
                "username": user.username, "email": user.email, 
                "rol": user.rol, "activo": user.activo, 
                "password_hash": get_password_hash(user.password),
                "id_usuario": id_usuario
            }
        else:
            update_query = """
                UPDATE usuarios 
                SET username = :username, email = :email, rol = :rol, activo = :activo
                WHERE id_usuario = :id_usuario
            """
            params = {
                "username": user.username, "email": user.email, 
                "rol": user.rol, "activo": user.activo, 
                "id_usuario": id_usuario
            }

        DatabaseConnection.execute_non_query(update_query, params)
        return {"success": True, "message": "Usuario actualizado exitosamente"}
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{id_usuario}")
def eliminar_usuario(id_usuario: int, current_user: dict = Depends(get_current_user_api)):
    try:
        if id_usuario == current_user.get('id_usuario'):
            raise HTTPException(status_code=403, detail="No puedes eliminar tu propia cuenta mientras estás logueado.")
            
        delete_query = "DELETE FROM usuarios WHERE id_usuario = :id"
        DatabaseConnection.execute_non_query(delete_query, {"id": id_usuario})
        
        return {"success": True, "message": "Usuario eliminado exitosamente"}
    except HTTPException as he:
        raise he
    except Exception as e:

        if "violates foreign key constraint" in str(e).lower():
            raise HTTPException(status_code=400, detail="No se puede eliminar el usuario porque tiene modelos o simulaciones asociadas.")
        raise HTTPException(status_code=500, detail=str(e))