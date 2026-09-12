# Instrucciones para ejecutar TalentMatch

El proyecto está configurado para ejecutarse utilizando **Docker** y **Docker Compose**. Esto levantará automáticamente la base de datos (PostgreSQL con pgvector), el backend principal y el servicio de Machine Learning (ML).

## 1. Prerrequisitos
Asegúrate de tener instalado [Docker](https://docs.docker.com/get-docker/) en tu sistema. (Docker Compose ya viene incluido en las versiones recientes de Docker Desktop o Docker Engine).

## 2. Ejecutar el proyecto
Abre una terminal, navega a la carpeta principal del proyecto (donde se encuentra el archivo `docker-compose.yml`) y ejecuta el siguiente comando:

```bash
docker compose up --build
```

> [!TIP]
> Si prefieres que la terminal quede libre (modo "detached" o segundo plano), puedes añadir la bandera `-d`:
> ```bash
> docker compose up -d 
> ```

## 3. Acceder a los servicios
Una vez que veas en la terminal que los contenedores están listos, podrás probar las APIs directamente desde tu navegador a través de Swagger UI:

- **API del Backend:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **API del ML Service:** [http://localhost:8001/docs](http://localhost:8001/docs)

## 4. Detener el proyecto
Si ejecutaste el proyecto sin `-d`, puedes detenerlo presionando `Ctrl + C` en la terminal.
Si quieres detener los servicios y limpiar la red creada, ejecuta:

```bash
docker compose down
```

> [!WARNING]
> Si deseas borrar también los volúmenes de datos (esto eliminará toda la información guardada en la base de datos), puedes ejecutar `docker compose down -v`.
