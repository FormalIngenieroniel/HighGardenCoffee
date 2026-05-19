# ☕ High Garden Coffee - Inteligencia Artificial para el Análisis Estratégico de Mercados

Este proyecto implementa una **Plataforma Analítica** diseñada para transformar datos históricos de consumo de café en ventajas competitivas. Integra un modelo de **Machine Learning (LightGBM)** con una muy buena precisión junto a un **Agente de IA Generativa** orquestado por LangChain y Google Gemini.

La solución está desplegada en una arquitectura de **microservicios distribuidos en la nube de AWS**, utilizando contenedores Docker para poder separar la capa de lógica (Backend) de la capa de presentación (Frontend), garantizando un entorno escalable y profesional para la toma de decisiones.

> 📄 **Documento oficial:** Para una descripcion mas detallada de la arquitectura, objetivos, and y resultados, leer el [**Documento final del proyecto**](Prueba%20Tec%20NTT%20Daniel%20Bernal.pdf).

> 📄 **Video de la presentacion:** Para una presentacion general de la arquitectura, codigo y demostracion en vivo, ver el [**Video de presentacion**]((https://youtu.be/Gi_zPpKof0w)).

---

#### 🤖 Introducción a la Arquitectura de IA
La inteligencia artificial usada en este proyecto no se enfoca en ser un chatbot, es un sistema que pueda actuar como un consultor basado en el razonamiento y prediccion de datos:
*   **Agente Consultor:** Es una entidad autónoma que es capaz de percibir el contexto del mercado, puede identificar brechas enlos datos y utiliza herramientas para realizar simulaciones.
*   **Consciencia de Contexto:** El agente no alucina, para lograrlo, fundamenta sus respuestas en un dataset y en las predicciones de un modelo LightGBM entrenado con 30 años de registros históricos.
*   **Orquestación:** Un flujo basado en herramientas (Tool Calling) que asegura que el agente "piense" y pueda seleccionar la mejor estrategia antes de entregar un analisis al usuario.

---

#### 🚀 Características Principales
*  ☁️  **Arquitecturaa Cloud Distribuida:** Desplegada en instancias AWS EC2 independientes (Frontend y Backend) para asegurar disponibilidad.
*  🐳  **Microservicios Dockerizados:** Cada capa corre en contenedores aislados.
*  🧠  **Predicciones buenas:** Modelo LightGBM entrenado con una estrategia de *Transfer Learning* logrando un **MAPE del 2.45%**.
*  🛠️  **Tool-Calling:** Uso de herramientas personalizadas para manejar datos desactualizados y simular impactos de precios.
*  ⚡  **Control de recursos:** Callback y estrategia personalizada para gestionar de forma estable las limitaciones de la Free Tier de Gemini.
*  📊  **Dashboard Interactivo:** Visualización dinámica de tendencias, proporciones de tipos de café y rankings de consumo.

---

#### 💻 Arquitectura del Sistema y Workflow
El proyecto se divide en dos capas principales que se comunican de forma segura dentro de la red privada de AWS:

1.  **Capa de Lógica (Backend):**
    *   **main_back.py:** Punto de entrada FastAPI que expone endpoints para datos de dashboard y el chat del agente.
    *   **agent_back.py:** Cerebro del sistema. Configura el agente de Gemini, define las herramientas y carga el modelo de forma nativa.

2.  **Capa de Presentación (Frontend):**
    *   **app_front.py:** Servidor FastAPI que renderiza la interfaz mediante plantillas **Jinja2**. Actúa como puente hacia el Backend.
    *   **script_front.js:** Lógica para la gestión del chat, renderizado de elementos del agente y gráficos.

---

#### 🧩 ¿Cómo funciona?
1.  **Input del Usuario:** El usuario pregunta sobre tendencias de consumo o impacto de precios en la interfaz web.
2.  **Enrutamiento Dinámico:** El agente evalúa si la consulta es válida, si faltan parámetros (como el precio global) o si el país tiene datos desactualizados.
3.  **Ejecución de Herramientas:** Si faltan datos, el agente activa `solicitar_parametro_exogeno`. Si los datos son viejos, busca un "Proxy" con comportamiento similar.
4.  **Inferencia:** El agente invoca el modelo LightGBM pasando las variables de entorno actuales para generar una proyección de variación de consumo.
5.  **Respuesta Estructurada:** El sistema devuelve la respuesta final y el historial de pasos lógicos (como las Tools utilizadas) para total control y transparencia.

---

#### 🧠 Lógica del Agente (Tools)
El sistema utiliza ingeniería de prompts y protocolos de comportamiento estrictos como lo son:
*   **Simular Impacto de Precio:** Ejecuta el modelo predictivo basado en variaciones porcentuales del precio global.
*   **País Proxy:** Identificca paises con estructuras de mercado muy parecidas para cubrir brechas de información histórica.
*   **Gestor de Exógenos:** Valida que esten las variables críticas antes de proceder y en caso de faltar, solicitarlas al usuario.

---

#### 🔧 Stack Tecnológico
*   **Infraestructura:** AWS EC2 (2 Instancias), Docker.
*   **Lenguajes:** Python 3.10.
*   **Frameworks IA:** LangChain, Google Gemini API, LightGBM.
*   **Web Frameworks:** FastAPI, Jinja2, Bootstrap.
*   **Data Science:** Pandas, Scikit-learn, Joblib.

---

#### 📊 Futuras Mejoras
*  🔄  **Migración a Copilot Studio:** Implementar la lógica de "Temas" para reducir costos de infraestructura y tiempo de desarrollo.
*  📈  **Nuevas Fuentes de Datos:** Ingesta de ddensidad demográfica y PIB per cápita para enriquecer la capacidad analítica del agente.
*  ☁️  **Mejora de capacidad:** Incrementar la capacidad para hacer llamados al LLM para poder integrar y profundizar en las Tools.

---

#### 👨‍💻 Autor
Desarrollado por Daniel Bernal para el Reto Técnico de High Garden Coffee.
