"""Pruebas de Carga y Rendimiento (Load & Performance Testing) con Locust para TalentMatch.

Permite simular múltiples usuarios concurrentes navegando vacantes,
consultando el estado del sistema y realizando solicitudes concurrentes.
"""
from locust import HttpUser, task, between


class TalentMatchUser(HttpUser):
    # Tiempo de espera simulado entre acciones de usuario (entre 0.5 y 2.0 segundos)
    wait_time = between(0.5, 2.0)

    @task(5)
    def test_healthcheck(self):
        """Monitorea el endpoint de salud del sistema."""
        self.client.get("/health", name="[GET] /health")

    @task(10)
    def test_listar_vacantes(self):
        """Simula usuarios navegando por el listado general de empleos."""
        self.client.get("/vacantes", name="[GET] /vacantes")

    @task(3)
    def test_filtrar_vacantes(self):
        """Simula búsqueda con paginación y filtros."""
        self.client.get("/vacantes?limit=5&offset=0", name="[GET] /vacantes?limit=5")

    @task(2)
    def test_auth_login_flow(self):
        """Simula intentos de inicio de sesión midiendo tiempo de respuesta y rate limiter."""
        with self.client.post(
            "/auth/login",
            json={"email": "usuario_prueba_carga@test.com", "password": "PasswordInvalido123!"},
            name="[POST] /auth/login (Simulation)",
            catch_response=True,
        ) as response:
            # 200 (éxito), 401 (rechazo de credenciales válido), 429 (rate limit activo)
            if response.status_code in [200, 401, 429]:
                response.success()
            else:
                response.failure(f"Código inesperado: {response.status_code}")
