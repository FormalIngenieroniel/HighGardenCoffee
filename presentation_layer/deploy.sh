#!/bin/bash
# Se limpiar contenedores e imágenes que esten "sueltas" para 
# liberar espacio en disco
docker system prune -f

# Construir la nueva imagen deteniendo y eliminando el contenedor 
# anterior de estar existiendo
docker build -t coffee-front .
docker stop coffee-front-container || true
docker rm coffee-front-container || true

# Se ejecutar el contenedor directamente con la IP privada de la 
# EC2 que contiene el backend o la capa lógica. Ademas, para tener
# la url mas limpia se decide mapear el puerto 80 de la EC2 al 
# 8000 (expuesto en el Dockerfile) del contenedor para no usar 
# puertos en la URL final de la web
docker run -d \
  --name coffee-front-container \
  -p 80:8000 \
  -e LOGIC_BACKEND_URL="http://172.31.65.154:8000" \
  coffee-front

echo "Frontend desplegado y corriendo en el puerto 80"