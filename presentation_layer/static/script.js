
// Logica para poder crear el carrusel "infinito" de los paises cuando la pagina web
// es renderizada.
document.addEventListener('DOMContentLoaded', () => {
    const tickerContent = document.getElementById('ticker-content');
    if (tickerContent) {
        tickerContent.innerHTML += tickerContent.innerHTML;
    }

    fetchDashboardData();
    setupModal();
});

// Logica para poder obtener los datos necesarios (procesados con pandas en el Backend)
// y poder pintar las graficas.
async function fetchDashboardData() {
    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();
        
        if(data.error) throw new Error(data.error);

        renderCoffeeTypeChart(data.coffee_types);
        renderTopConsumersChart(data.top_consumers);
        renderPriceTrendChart(data.price_trend);
    } catch (error) {
        console.error("Error cargando el dashboard:", error);
    }
}

// Logica para mostrar de manera correcta la grafica de pastel mostrando la proporcion
// de consumo de cada uno de los tipos.
function renderCoffeeTypeChart(coffeeData) {
    const ctx = document.getElementById('coffeeTypeChart').getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(coffeeData),
            datasets: [{
                data: Object.values(coffeeData),
                backgroundColor: ['#D35400', '#2C3E50', '#E67E22', '#34495E']
            }]
        },
        options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
    });
}

// Logica para mostrar de manera correcta la de barras que se encarga de mostrar el
// top 5 consumidores de cafe.
function renderTopConsumersChart(topData) {
    const ctx = document.getElementById('topConsumersChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: topData.labels,
            datasets: [{
                label: 'Consumo',
                data: topData.data,
                backgroundColor: '#2C3E50'
            }]
        },
        options: { 
            indexAxis: 'y', 
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } } 
        }
    });
}

// Logica para mostrar de manera correcta la grafica del precio global del cafe, para
// poder apreciar como ha cambiado con el tiempo.
function renderPriceTrendChart(trendData) {
    const ctx = document.getElementById('priceTrendChart').getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: trendData.labels,
            datasets: [{
                label: 'Precio Promedio',
                data: trendData.data,
                borderColor: '#D35400',
                tension: 0.1,
                fill: false
            }]
        },
        options: { responsive: true, plugins: { legend: { display: false } } }
    });
}

// Logica para poder captar de manera correcta la pregunta que tenga el usuario
// al momento de envir el formulrio para que el LLM pueda ver la pregunta.
document.getElementById('chat-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const inputField = document.getElementById('user-input');
    const userText = inputField.value.trim();
    if (!userText) return;

    const chatBox = document.getElementById('chat-box');
    const thoughtsBox = document.getElementById('thoughts-box');

    appendMessage('user', userText);
    inputField.value = '';
    
    thoughtsBox.innerHTML = '<span class="loading">Iniciando inferencia con Gemini y LightGBM...</span>';
    
    try {
        const formData = new FormData();
        formData.append('user_input', userText);

        const response = await fetch('/ask', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error("Error en la respuesta del servidor frontend");

        const data = await response.json();

        appendMessage('agent', data.final_answer);
        renderThoughts(data.agent_thoughts, thoughtsBox);

    } catch (error) {
        appendMessage('error', 'Ocurrió un error al conectar con el backend. Revisa los logs.');
        thoughtsBox.innerHTML = '<span style="color:#f44336;">Error de comunicación.</span>';
        console.error(error);
    }
});

// Logica para mostrar de manera correcta los mensajes que se han compartido el
// usuario y el LLM (apariencia de chat)
function appendMessage(sender, text) {
    const chatBox = document.getElementById('chat-box');
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender);
    msgDiv.textContent = text;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Logica para mostrar de manera correcta los pasos logicos del LLM al procesar
// la peticion enviada por el usuario (las Tools que utilizo y razonaminetos)
function renderThoughts(thoughts, container) {
    if (!thoughts || thoughts.length === 0) {
        container.innerHTML = '<em>Inferencia directa generada. No se requirió llamar herramientas externas.</em>';
        return;
    }
    let html = '';
    thoughts.forEach((step, index) => {
        html += `<div class="thought-step">
            <strong>[Paso ${index + 1}] Tool: ${step.tool_called}</strong><br>
            <span class="tool-input">> Input: ${JSON.stringify(step.tool_input)}</span><br>
            <span class="observation">> Output: ${JSON.stringify(step.observation)}</span>
        </div><hr>`;
    });
    container.innerHTML = html;
}

// Se configura la manera en la que se van a mostrar los datos completos,
// se opto por utilizar un modal para la facilidad del usuario
function setupModal() {
    const modal = document.getElementById("dataModal");
    const btn = document.getElementById("btn-full-data");
    const span = document.getElementsByClassName("close-btn")[0];

    btn.onclick = async function() {
        modal.style.display = "block";
        await fetchAndRenderCSV();
    }

    span.onclick = function() {
        modal.style.display = "none";
    }

    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }
}

// Logica para mostrar de manera correcta los datos completos del
// CSV que contiene la informacion de cada pais.
async function fetchAndRenderCSV() {
    const tableHeaders = document.getElementById('tableHeaders');
    const tableBody = document.getElementById('tableBody');
    
    try {
        const response = await fetch('/api/csv_data');
        const data = await response.json();
        
        if (data.error) throw new Error(data.error);
        if (data.length === 0) {
            tableBody.innerHTML = '<tr><td>No hay datos disponibles.</td></tr>';
            return;
        }

        const columns = Object.keys(data[0]);
        tableHeaders.innerHTML = columns.map(col => `<th>${col}</th>`).join('');
        
        const rowsHtml = data.map(row => {
            return `<tr>${columns.map(col => `<td>${row[col] !== null ? row[col] : ''}</td>`).join('')}</tr>`;
        }).join('');
        
        tableBody.innerHTML = rowsHtml;

    } catch (error) {
        tableBody.innerHTML = `<tr><td style="color:red;">Error cargando datos: ${error.message}</td></tr>`;
    }
}