FROM python:3.10-slim
WORKDIR /app

# Importante hacer la instalacion para poder leer el modelo lgb
# de manera nativa y no haayn incompatibilidades con el wrap que
# hace sklearn.
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Se expone el puerto 8000 asegurandonos que el trafico solo sea 
# permitido de la EC2 del front mediante inbound rules en AWS
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]