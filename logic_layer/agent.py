import os
import time
import pandas as pd
import lightgbm as lgb
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.callbacks import BaseCallbackHandler

# Se carga la base de datos para poder realizar todas las operaciones de prediccion
# calculo de graficas y envio de informacion al Frontend.
df_paises = pd.read_csv("estado_actual_paises.csv")

# Se hace una carga segura del modelo LightGBM en formato nativo, si hace en con
# Joblib se tienen incompatibilidades nativas de Sklearn. Es mas rapido y mas estable
# esto funciona gracias a que lgbm se guarda como archivo de texto con árboles pesos
# reglas y splits.
modelo_path = "modelo_lgbm_cafe_booster.txt"
if os.path.exists(modelo_path):
    modelo_lgbm = lgb.Booster(model_file=modelo_path)
else:
    modelo_lgbm = None

# Se crea un callback personalizado para poder lidiar con la api keys gratuitas de 
# Gemini, la cual se bloquea si se hacen muchas peticiones en poco tiempo.
class RateLimitCallbackHandler(BaseCallbackHandler):
    """
    Este callback intercepta cada vez que el agente está a punto de hacerle 
    una petición al modelo de Google y fuerza una pausa.
    """
    def __init__(self, delay: float = 5.0):
        self.delay = delay

    def on_llm_start(self, serialized, prompts, **kwargs):
        print(f"\n[CallB Rate Limit] Esperando {self.delay} segundos antes de consultar al LLM para no violar la cuota gratuita")
        time.sleep(self.delay)

# Se define la primera tool que el agente va a utilizar, es importante que se
# especifique la variacion para realizar la prediccion del consumo. Al ser un
# modelo autoregresivo, necesito de ciertos datos como el precio global o su
# porcentaje de variacion, de esta manera puede hacer la prediccion.
@tool
def simular_impacto_precio(pais: str, variacion_porcentual: float):
    """
    Usa esta herramienta EXCLUSIVAMENTE cuando el usuario solicita predecir el consumo futuro de un país 
    y el usuario YA ha especificado explícitamente un precio global o un porcentaje de variación.
    ¡CRÍTICO!: NO inventes, asumas, ni infieras el valor de 'variacion_porcentual'. 
    Si el usuario dice "se mantiene", el valor es 0.0.
    """
    pais_clean = pais.strip().title()
    datos_pais = df_paises[df_paises['Country'].str.title() == pais_clean]
    
    if datos_pais.empty:
        return f"Error: No se encontraron registros para el país '{pais}'."
    
    # Una vez ya se tiene el pais al que se le hara la prediccion, se toma la última fila histórica conocida 
    # para construir los lags del próximo año y tener informacion necesaria para la prediccion.
    ultima_fila = datos_pais.sort_values(by='Year_num').iloc[-1]
    
    try:
        # Se ordenan las columnas para realizar la prediccion igual que en el entrenamiento.
        columnas_modelo = [
            "Year_num", "Global_price_Lag1", "Lag_1", "Lag_2", "Lag_3",
            "Rolling_Mean_3", "Rolling_STD_3", "Price_Change_Lag1",
            "Consumption_Change_Lag1", "Coffee type", "Country", "Market_Size"
        ]
        
        # Se construyen las variables para el Año T+1 solicitado junto con la 'variacion_porcentual' que dio el 
        # usuario como la variable que refleja el cambio de precio. De esta manera se tendrian todas las variables
        # para realizar la prediccion.
        row_data = {
            "Year_num": int(ultima_fila["Year_num"]) + 1,
            "Global_price_Lag1": float(ultima_fila["Global_price"]) if "Global_price" in ultima_fila else float(ultima_fila["Global_price_Lag1"]), 
            "Lag_1": float(ultima_fila["Consumption"]), 
            "Lag_2": float(ultima_fila["Lag_1"]),       
            "Lag_3": float(ultima_fila["Lag_2"]),       #
            "Rolling_Mean_3": float(ultima_fila["Rolling_Mean_3"]),
            "Rolling_STD_3": float(ultima_fila["Rolling_STD_3"]),
            "Price_Change_Lag1": float(variacion_porcentual),
            "Consumption_Change_Lag1": float(ultima_fila["Consumption_Change"]),
            "Coffee type": ultima_fila["Coffee type"],
            "Country": pais_clean,
            "Market_Size": ultima_fila["Market_Size"]
        }
        
        features_df = pd.DataFrame([row_data], columns=columnas_modelo)
        
        for col in ["Coffee type", "Country", "Market_Size"]:
            features_df[col] = features_df[col].astype("category")
            
        # Se hace la preddiocn y se realiza el procesamiento necesario (igual que en el Notebook) del modelo
        # parap oder determinar el consumo real.
        prediccion_cambio = modelo_lgbm.predict(features_df)[0]
        
        consumo_anterior = row_data["Lag_1"]
        consumo_proyectado = consumo_anterior * (1 + prediccion_cambio)

        cambio_pct_usuario = prediccion_cambio * 100
        
        return {
            "status": "success",
            "pais": pais_clean,
            "consumo_proyectado": round(float(consumo_proyectado), 2),
            "consumo_anterior": round(float(consumo_anterior), 2),
            "cambio_porcentaje": round(float(cambio_pct_usuario), 2),
            "escenario_precio_simulado": variacion_porcentual
        }
        
    except Exception as e:
        return f"Error interno al procesar la predicción: {str(e)}. Verifica que tu archivo CSV (df_paises) contenga todas las columnas calculadas en el notebook."

# Se define la siguiente tool que el agente podra utilizar, esta es para cuando
# el usuario este preguntando por un pais que tiene sus datos altamente desactualizados
# en este caso el agente debera proveer una opcion confiable para realizar una
# prediccion. Esta opcion confiable debe ser parecida al pais que se intento 
# predecir en primer lugar.
@tool
def buscar_country_proxy(pais_objetivo: str, target_year: int):
    """
    Usa esta herramienta cuando los datos del país consultado estén desactualizados (brecha > 3 años) 
    y el año solicitado sea menor o igual a 2020.
    """
    pais_clean = pais_objetivo.strip().title()
    datos_target = df_paises[df_paises['Country'].str.title() == pais_clean]
    
    if datos_target.empty:
        return f"Error: El país {pais_objetivo} no existe en los registros."
      
    # Se debe realizar la busqueda de tal manera que el tipo de cafe y el tamaño sean iguales que el pais
    # que se queria predecir en primer lugar pero no tenia los datos. El nuevo pais a buscar debe tener
    # Sus datos completos.
    tipo_cafe = datos_target['Coffee type'].iloc[0]
    tamanio_mercado = datos_target['Market_Size'].iloc[0]
    ultimo_anio = int(datos_target['Year_num'].max())
    
    proxies = df_paises[
        (df_paises['Country'].str.title() != pais_clean) &
        (df_paises['Coffee type'] == tipo_cafe) &
        (df_paises['Market_Size'] == tamanio_mercado) &
        (df_paises['Year_num'] >= 2019)
    ]['Country'].unique().tolist()
    
    return {
        "pais_original": pais_clean,
        "ultimo_anio_registrado": ultimo_anio,
        "target_year": target_year,
        "tipo_cafe": tipo_cafe,
        "market_size": tamanio_mercado,
        "proxies_encontrados": proxies[:3]
    }

# Esta herramienta es para cuando el agente detecte que se deba hacer una simulacion
# que este muy lejos en el tiempo, por ejemplo, si se pide un consumo en el 2027, en
# este caso el agente debera solicitar mas informacion al usuario para poder crear
# la coleccion de datos para realizar la prediccion. En este momento esta herramienta
# esta en desarrollo, la logica esta construida pero no implementada porque las 
# limitaciones de la api gratuita de gemini no soportan tantas llamadas y consumo.
@tool
def simulacion_what_if_global(pais: str, year_solicitado: int):
    """
    Usa esta herramienta exclusivamente cuando el año solicitado es estrictamente mayor a 2020.
    """
    return {
        "pais": pais.strip().title(),
        "year_solicitado": year_solicitado,
        "contexto": "Estancamiento global. Forzar cambio a modo simulación de estrés / What-If."
    }

# Esta herramienta se llama una vez que el agente determina que falta un parametro
# importante para poder realizar la prediccion.
@tool
def solicitar_parametro_exogeno(pais: str):
    """
    Usa esta herramienta cuando la consulta de predicción de consumo es válida temporalmente,
    pero el usuario omitió definir el valor del Precio Global en su prompt original.
    """
    return {
        "pais": pais.strip().title(),
        "status": "missing_exogenous_variable"
    }


# Se realiza la configuracion del Agente con el modelo de Google, se utiliza una
# temperatura baja para que el analisis sea mas "determinista". Se definen los 
# reintentos y el delay para que no se hagan muchas llamadas en poco tiempo y
# violen las normas de la free tier de la key de Gemini.
#
# Las reglas de negocio tienen la finalidad de que el agente pueda ser usado
# como un router dinamico segun cada caso que el usuario quiera evaluar. En resumen
# las reglas se basan en, primero si el usuario esta intentando predecir un precio
# (Por ahora el agente solo predice tendencias) Segundo, si los datos son muy
# viejos. Tercero, si el año esta muy lejos para hacer la prediccion. Cuarto, si
# hay datos faltantes y por ultimo si es valida.
def setup_agent():

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        temperature=0.1, 
        max_retries=3,
        callbacks=[RateLimitCallbackHandler(delay=5.0)] 
    ) 
    
    tools = [simular_impacto_precio, buscar_country_proxy, simulacion_what_if_global, solicitar_parametro_exogeno]
    
    resumen_lags = {}
    for c in df_paises['Country'].unique():
        df_c = df_paises[df_paises['Country'] == c]
        resumen_lags[c] = int(df_c['Year_num'].max())
        
    resumen_lags_str = "\n    ".join([f"- {pais}: {anio}" for pais, anio in resumen_lags.items()])
        
    system_prompt = f"""
    Eres un Científico de Datos Experto y Consultor Estratégico Senior especializado en el Mercado Global del Café. 
    Tu objetivo principal no es solo arrojar números, sino analizar e interpretar tendencias para otorgar una ventaja competitiva en el mercado.

    MAPPING DE CONTROL TEMPORAL (Último año con datos reales por país):
    {resumen_lags_str}
    Año límite máximo global absoluto de la base de datos: 2020.

    INSTRUCCIÓN CRÍTICA DE RESPUESTA:
    Después de invocar CUALQUIER herramienta y recibir su resultado (observation), DEBES procesar esa información y generar una respuesta final en lenguaje natural dirigida al usuario. Nunca termines tu turno sin dar una respuesta conversacional.

    REGLAS DE NEGOCIO Y ENRUTAMIENTO OBLIGATORIAS (Sigue este orden de prioridades):

    1. BLOQUEO DE PREDICCIÓN DE PRECIO (Escenario 1):
       - Si la intención es predecir el precio, NO LLAMES TOOLS. Responde: "Mi modelo analítico está diseñado para predecir con alta precisión cómo reaccionará el consumo de café en cada país, pero no para pronosticar el precio global del mercado. Sin embargo, puedo ayudarte con una simulación financiera: si me das un precio global estimado o un porcentaje de aumento/caída para el próximo año, puedo decirte exactamente cómo impactará eso en la demanda de los países que te interesen. ¿Qué escenario de precio te gustaría simular?"

    2. ESTANCAMIENTO GLOBAL DE DATOS (Escenario 3):
       - Si el año solicitado es > 2020, llama a 'simulacion_what_if_global'.
       - Respuesta final OBLIGATORIA: "Actualmente, nuestra base de datos tiene su último corte global en el año 2020. No puedo ofrecer un pronóstico temporal exacto para [Año Solicitado] sin la información de los años intermedios. Lo que sí podemos hacer es un análisis de escenarios (What-If) partiendo del último estado conocido. Si me indicas qué condiciones esperas para [Año Solicitado] (por ejemplo, ¿crees que el precio global subirá un 10% respecto a los niveles de 2020? ¿O que habrá una contracción en mercados grandes?), puedo simular cómo reaccionará la demanda y qué países presentarán las mejores oportunidades bajo esas condiciones."

    3. EFECTO BOLA DE NIEVE / DATOS DESACTUALIZADOS (Escenario 2):
       - Si (Año Solicitado - Último Año Registrado) > 3, DEBES llamar a 'buscar_country_proxy'.
       - Respuesta final OBLIGATORIA con datos devueltos: "Para [País Original], los últimos datos registrados son del año [Último Año del País]. Proyectar el consumo hasta [Año Solicitado] generaría un margen de error demasiado alto debido al tiempo transcurrido. Como alternativa más confiable, he buscado mercados con un comportamiento histórico y características similares (Market_Size: [Market Size], mismo tipo de café). Te propongo utilizar a [Lista de países proxies devueltos] como modelo de referencia. Sus datos están actualizados a 2020. ¿Te gustaría que corra la predicción sobre este mercado para que tengas una idea de la tendencia actual en este segmento?"

    4. AMBIGÜEDAD EN VARIABLES EXÓGENAS (Escenario 4):
       - Si la consulta es válida temporalmente pero NO se incluyó un precio global, llama a 'solicitar_parametro_exogeno'.
       - Respuesta final OBLIGATORIA: "Puedo proyectar el consumo de [País] para el próximo periodo, pero la demanda está fuertemente ligada a las fluctuaciones del precio global. ¿Tienes algún estimado de a cuánto estará el precio global del café? Si no estás seguro, podemos correr tres simulaciones rápidas: un escenario conservador (precio se mantiene), un escenario alcista (+5%) y un escenario a la baja (-5%). ¿Cómo prefieres proceder?"

    5. INFERENCIA EXITOSA (Simulación Numérica Real):
       - Si todo está en orden y HAY un precio, llama a 'simular_impacto_precio'.
       - Responde con los resultados numéricos de consumo y añade un análisis comercial estratégico.
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, return_intermediate_steps=True, max_iterations=3, verbose=True)
    return agent_executor