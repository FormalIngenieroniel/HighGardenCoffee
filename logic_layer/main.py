import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from agent import setup_agent, df_paises

# Se inicializa la app de FastAPI para poder crear y conectar los diferentes
# endpoints que se encargaran de mandaran al front los diferentes datos.
# Tambien se inicializa el agente.
app = FastAPI()
agent_executor = setup_agent()

# Nos aseguramos con pydantic que la peticion al agente siempre tendra el
# formato correcto.
class Query(BaseModel):
    user_input: str

# Este endpoint se encarga de recolectar los paises unicos que se encuentran
# en el df para devolverlos como un JSON.
@app.get("/paises")
def get_paises():
    """Endpoint que se encarga de devolver la lista de países disponibles en el CSV al Frontend."""
    paises = df_paises['Country'].unique().tolist()
    return {"paises": paises}
    
# Este endpoint se encarga de procesar los datos del CSV con pandas para poder
# entregarlos al Frontend y que se pinten las graficas de la mejor manera.
@app.get("/dashboard_data")
def get_dashboard_data():
    """Endpoint que se encarga de calcular y devolver los datos que se necesitan en los gráficos del Frontend."""
    
    # Informacion para el grafico de pastel.
    coffee_counts = df_paises['Coffee type'].value_counts().to_dict()
    
    # Informacion para el grafico de barras de top 5 consumidores.
    latest_year = df_paises['Year_num'].max()
    latest_data = df_paises[df_paises['Year_num'] == latest_year]
    top_5_df = latest_data.nlargest(5, 'Consumption')[['Country', 'Consumption']]
    top_5 = {"labels": top_5_df['Country'].tolist(), "data": top_5_df['Consumption'].tolist()}
    
    # Informacion necesaria para el grafico del comportamineto del precio.
    price_trend_df = df_paises.groupby('Year_num')['Global_price'].mean().dropna().sort_index()
    price_trend = {"labels": price_trend_df.index.tolist(), "data": price_trend_df.tolist()}
    
    return {
        "coffee_types": coffee_counts,
        "top_consumers": top_5,
        "price_trend": price_trend
    }
    
# Este endpoint se encarga de procesar enviar todos los datos del CSV al Front.
@app.get("/csv_data")
def get_csv_data():
    """Endpoint que se encarga de devolver el dataset completo para la visualización en tabla."""

    df_clean = df_paises.where(pd.notnull(df_paises), None)
    return df_clean.to_dict(orient="records")
    
# Este endpoint se encarga de procesar las preguntas correctamente que llegan
# desde el Front para capturar las respuestas y pensamiento del Agente.
@app.post("/chat")
async def chat_with_agent(query: Query):
    """Endpoint que se encarga de recibir las preguntas al LLM del frontend y extraer las respuestas y pensamiento interno."""
    response = agent_executor.invoke({"input": query.user_input})
    
    thought_process = []
    for action, observation in response.get("intermediate_steps", []):
        thought_process.append({
            "tool_called": action.tool,
            "tool_input": action.tool_input,
            "observation": observation
        })
        
    return {
        "final_answer": response["output"],
        "agent_thoughts": thought_process
    }