# main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Importamos todos los routers
from routers import auth, datos, simulacion, habitat, conectividad, reportes



app = FastAPI(
    title="Gemelo Digital API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registramos las rutas
app.include_router(auth.router, prefix="/api/auth", tags=["Autenticación"])
app.include_router(datos.router, prefix="/api/datos", tags=["Datos y Catálogos"])
app.include_router(simulacion.router, prefix="/api/simulacion", tags=["Simulaciones Climáticas"])
app.include_router(habitat.router, prefix="/api/habitat", tags=["Modelos de Hábitat"])
app.include_router(conectividad.router, prefix="/api/conectividad", tags=["Conectividad"])
app.include_router(reportes.router, prefix="/api/reportes", tags=["Reportes"])



# PREVENCIÓN: Crear la carpeta antes de montarla
os.makedirs("static/simulaciones", exist_ok=True)

# Montamos la carpeta de recursos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return {"status": "ok", "message": "API del Gemelo Digital en línea"}