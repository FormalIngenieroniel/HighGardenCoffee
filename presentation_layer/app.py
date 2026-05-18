from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
import os

# Se crea la capa intermedia entre las dos instancias EC2 (Presentacio
# y logica) pricipalmente inicializando "app" como un servidor web
# que tendra todas las rutas y se lee la variable de entorno que tendra
# la IP privada de la EC2 con la logica.
app = FastAPI()
LOGIC_BACKEND_URL = os.getenv("LOGIC_BACKEND_URL", "http://127.0.0.1:8000")

# Nos asegurmos que FastAPI pueda tener acceso a todos los archivos y
# elementos que se encuentran en static y que el HTML (par ser renderizado
# por Jinja) se encuentra en templates.
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Esta es la ruta principal de la app, la cual se encarga de hacer una
# peticion que traiga los paises que estan en la logica de la aplicacion.
# De fallar se tiene un cath que no deja que se rompa la app y retorna
# la pagina renderizada con la variable de paises para poder ser utilizada
# en las funciones de la web.
#
# Se decidio por tener este Endpoint solo extrayendo los paises para
# poder hacer un testeo base donde se probaba la conexion con la EC2 del
# Backend y si estaba enviando los paises correctamente solo ingresando al
# portal web. 
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Endpoint base que se encarga de extraer los datos de basicos de los paises desde el frontend y renderizar el HTML."""
    try:
        response = requests.get(f"{LOGIC_BACKEND_URL}/paises")
        paises = response.json().get("paises", [])
    except:
        paises = ["Error cargando países - Revisa la conexión al Backend"]
        
    return templates.TemplateResponse(
        request=request,
        name="index.html", 
        context={"request": request, "paises": paises}
    )

# Este endpoint se encarga de pedir los datos procesados con pandas en
# el backend para poder realizar las pequeñas graficas que se encuentran
# en la parte izquierda de la interfaz web.
@app.get("/api/dashboard")
async def get_dashboard():
    """Endpoint que se encarga de extraer los datos de gráficos vía AJAX desde el frontend."""
    try:
        response = requests.get(f"{LOGIC_BACKEND_URL}/dashboard_data")
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# Este endpoint se encarga de pedir todos los datos almacenados en el csv
# de los datos ocmpletos de los paises y poder mostrarlos con una opcion
# especial en la seccion de los graficos.
@app.get("/api/csv_data")
async def get_csv_data():
    """Endpoint que se encarga de extraer el dataset completo desde el frontend."""
    try:
        response = requests.get(f"{LOGIC_BACKEND_URL}/csv_data")
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# Este endpoint se encarga de mandar una pregunta del usuario al Backend
# para que esta pueda ser leida y extraer la respuesta por el LLM para 
# mostrarla en la web.
@app.post("/ask")
async def ask_agent(user_input: str = Form(...)):
    """Endpoint que se encarga de mandar las preguntas al LLM desde el frontend y extraer las respuestas desde el Backend."""
    try:
        response = requests.post(f"{LOGIC_BACKEND_URL}/chat", json={"user_input": user_input})
        data = response.json()
        return data
    except Exception as e:
        return {"final_answer": f"Error de conexión con el LLM: {str(e)}", "agent_thoughts": []}