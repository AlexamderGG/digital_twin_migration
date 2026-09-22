import os
from dotenv import load_dotenv
from groq import Groq

# Cargar la API Key desde tu archivo .env
load_dotenv()

try:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    modelos = client.models.list()
    
    print("\n🟢 Modelos disponibles para tu API Key:")
    print("-" * 40)
    for m in modelos.data:
        print(f"- {m.id}")
    print("-" * 40)
        
except Exception as e:
    print(f"🔴 Error al consultar los modelos: {e}")