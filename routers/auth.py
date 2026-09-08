# backend/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from modules.auth import AuthManager

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    session = AuthManager.login(form_data.username, form_data.password)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "access_token": session.token, 
        "token_type": "bearer", 
        "user": {
            "id_usuario": session.id_usuario,
            "username": session.username,
            "nombre_completo": session.nombre_completo,
            "rol": session.nombre_rol,
            "permisos": session.permisos
        }
    }

def get_current_user_api(token: str = Depends(oauth2_scheme)):
    payload = AuthManager.decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    return payload