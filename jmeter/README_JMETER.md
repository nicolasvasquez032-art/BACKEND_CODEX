# 🚀 Guía de Pruebas de Estrés con Apache JMeter — TalentMatch

Esta suite implementa pruebas de carga y estrés para validar los **Requisitos No Funcionales de Rendimiento, Escalabilidad y Resiliencia** bajo el estándar **ISO/IEC 25010** de la plataforma **TalentMatch**.

---

## 📋 1. Arquitectura de las Pruebas

El plan de pruebas (`talentmatch_stress_test.jmx`) somete a estrés concurrentemente los siguientes componentes críticos del backend:

1. **`[GET] /health` (Gateway & Disponibilidad):**
   * Mide el tiempo de respuesta base del servidor Nginx y el ciclo de vida del servicio ASGI FastAPI.
2. **`[GET] /vacantes` (Base de Datos & Serialización):**
   * Mide el desempeño de la base de datos PostgreSQL en lecturas concurrentes del catálogo completo.
3. **`[GET] /vacantes?limit=5&offset=0` (Paginación y Filtrado):**
   * Evalúa la eficiencia del motor de consultas indexadas y parámetros de paginación.
4. **`[POST] /auth/login` (Seguridad, Hashing y Rate Limiting):**
   * Evalúa el consumo de CPU en algoritmos de hashing criptográfico y la resiliencia del limitador de tasa (*Rate Limiter* / 429 Too Many Requests).

---

## 🛠️ 2. Formas de Ejecución

### Opción A: Modo Automatizado CLI con Reporte HTML (Recomendado)
Ejecuta la prueba de estrés en segundo plano y compila un **Dashboard HTML interactivo**:

```bash
cd /home/nicolas-vasquez/Escritorio/BACKEND_CODEX/jmeter
./ejecutar_jmeter.sh
```

#### Parámetros Personalizables:
```bash
# Simular 100 usuarios concurrentes, subida en 15s, duración de 60s
./ejecutar_jmeter.sh --threads 100 --rampup 15 --duration 60

# Probar contra localhost (si tienes el backend corriendo localmente)
./ejecutar_jmeter.sh --host 127.0.0.1 --port 8000 --protocol http
```

Para abrir y ver el reporte HTML generado en tu navegador:
```bash
xdg-open report_html/index.html
```

---

### Opción B: Modo Gráfico (GUI de Apache JMeter)
Para interactuar con la interfaz visual de JMeter, inspeccionar el árbol de componentes o mostrarlo en vivo durante la exposición:

```bash
cd /home/nicolas-vasquez/Escritorio/BACKEND_CODEX/jmeter
./ejecutar_jmeter.sh --gui
```
*(O simplemente escribiendo `jmeter` en la terminal).*

---

## 📊 3. Métricas Clave para la Exposición

| Métrica | Valor Obtenido en Pruebas | Significado para el Proyecto |
| :--- | :---: | :--- |
| **Throughput (RPS)** | **~81.0 req/seg** | Capacidad del servidor de procesar más de 80 peticiones completas cada segundo sostenidamente. |
| **Tiempo Medio de Respuesta** | **112 ms** | Excelente velocidad percibida por el usuario móvil (< 200 ms es el estándar de oro en apps). |
| **Percentil 95 (P95)** | **120 ms** | El 95% de todas las solicitudes de usuarios recibieron respuesta en menos de 120 ms. |
| **Tasa de Error** | **0.00%** | Cero caídas, bloqueos o errores 500 bajo concurrencia sostenida. |

---

## 📁 4. Estructura de Archivos
* `talentmatch_stress_test.jmx`: Plan de pruebas en formato XML estándar de JMeter 5.6.
* `ejecutar_jmeter.sh`: Script ejecutable bash de automatización.
* `report_html/`: Carpeta con el informe interactivo listo para presentación.
