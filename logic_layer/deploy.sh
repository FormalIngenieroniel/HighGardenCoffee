#!/bin/bash

# Primero nos aseguramos que el disco del a EC2 este limpio para poder
# comenzar a construir la imagen de Docker y que no hayan otros contendores
# antiguos
echo "Se limpia el disco"
docker system prune -f
echo "Se construye la imagen coffee-logic"
docker build -t coffee-logic .
echo "Se deteniene y elimina contenedor anterior"
docker stop coffee-logic-container || true
docker rm coffee-logic-container || true

# Se levanta el nuevo contenedor en el puerto correspondiente y con la api
# key de gemini para realizar las peticiones
echo "Se levanta el nuevo contenedor"
docker run -d \
  --name coffee-logic-container \
  -p 8000:8000 \
  -e GOOGLE_API_KEY="$GOOGLE_API_KEY" \
  coffee-logic

echo "Backend Lógico corriendo en el puerto 8000"