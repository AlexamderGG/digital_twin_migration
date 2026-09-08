# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importamos todos los routers
from routers import auth, datos, simulacion, habitat, conectividad


app = FastAPI(
    title="Gemelo Digital API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
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

@app.get("/")
def root():
    return {"status": "ok", "message": "API del Gemelo Digital en línea"}