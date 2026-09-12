"""Implementaciones fake (in-memory) de los puertos para tests unitarios.

Estos fakes NO usan base de datos, FastAPI, SQLAlchemy ni ningún framework.
Permiten testear casos de uso de forma aislada y rápida.
"""
from datetime import datetime
from uuid import UUID, uuid4

from domain.entities.candidate_profile import CandidateProfile
from domain.entities.password_reset_token import PasswordResetToken
from domain.entities.user import User, UserRole


# ── Repositorio fake ──────────────────────────────────────────────────────────

class FakeUserRepository:
    """Repositorio en memoria que implementa UserRepositoryPort."""

    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}
        self.profiles: dict[UUID, CandidateProfile] = {}
        self.reset_tokens: dict[UUID, PasswordResetToken] = {}

    async def find_by_email(self, email: str) -> User | None:
        return next((u for u in self.users.values() if u.email == email), None)

    async def find_by_id(self, user_id: UUID) -> User | None:
        return self.users.get(user_id)

    async def create_user(self, email: str, password_hash: str, role: str) -> User:
        from domain.exceptions import EmailAlreadyRegisteredError
        if any(u.email == email for u in self.users.values()):
            raise EmailAlreadyRegisteredError(f"{email} ya registrado")
        user = User(
            id=uuid4(),
            email=email,
            password_hash=password_hash,
            role=UserRole(role),
            created_at=datetime.utcnow(),
        )
        self.users[user.id] = user
        return user

    async def update_user_password(self, user_id: UUID, new_password_hash: str) -> None:
        user = self.users.get(user_id)
        if user:
            from dataclasses import replace
            self.users[user_id] = replace(user, password_hash=new_password_hash)

    async def create_candidate_profile(
        self,
        user_id: UUID,
        full_name: str,
        skills: list[str],
        experience_years: int,
        location: str | None,
        education: str | None,
    ) -> CandidateProfile:
        profile = CandidateProfile(
            id=uuid4(),
            user_id=user_id,
            full_name=full_name,
            skills=skills,
            experience_years=experience_years,
            location=location,
            education=education,
        )
        self.profiles[profile.id] = profile
        return profile

    async def get_candidate_profile_by_user_id(self, user_id: UUID) -> CandidateProfile | None:
        return next((p for p in self.profiles.values() if p.user_id == user_id), None)

    async def get_candidate_profile_by_id(self, profile_id: UUID) -> CandidateProfile | None:
        return self.profiles.get(profile_id)

    async def update_candidate_profile(
        self,
        profile_id: UUID,
        full_name: str,
        skills: list[str],
        experience_years: int,
        location: str | None,
        education: str | None,
    ) -> CandidateProfile:
        from domain.exceptions import ProfileNotFoundError
        profile = self.profiles.get(profile_id)
        if profile is None:
            raise ProfileNotFoundError(f"Perfil {profile_id} no encontrado")
        from dataclasses import replace
        updated = replace(
            profile,
            full_name=full_name,
            skills=skills,
            experience_years=experience_years,
            location=location,
            education=education,
        )
        self.profiles[profile_id] = updated
        return updated

    async def update_cv_text(self, profile_id: UUID, cv_text: str) -> CandidateProfile:
        from domain.exceptions import ProfileNotFoundError
        profile = self.profiles.get(profile_id)
        if profile is None:
            raise ProfileNotFoundError(f"Perfil {profile_id} no encontrado")
        from dataclasses import replace
        updated = replace(profile, cv_text=cv_text)
        self.profiles[profile_id] = updated
        return updated

    async def create_password_reset_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        token = PasswordResetToken(
            id=uuid4(),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.reset_tokens[token.id] = token
        return token

    async def find_password_reset_token(self, token_hash: str) -> PasswordResetToken | None:
        return next(
            (t for t in self.reset_tokens.values() if t.token_hash == token_hash),
            None,
        )

    async def mark_token_used(self, token_id: UUID) -> None:
        token = self.reset_tokens.get(token_id)
        if token:
            from dataclasses import replace
            self.reset_tokens[token_id] = replace(token, used=True)


# ── Hasher fake ───────────────────────────────────────────────────────────────

class FakePasswordHasher:
    """Hasher determinista que simplemente prefija el texto con 'hashed:'."""

    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, plain: str, hashed: str) -> bool:
        return hashed == f"hashed:{plain}"


# ── Token service fake ────────────────────────────────────────────────────────

class FakeTokenService:
    """Token service que devuelve un string fijo para facilitar asserts."""

    def create_access_token(self, user: User) -> str:
        return f"fake_token_for_{user.email}"


# ── Email service fake ────────────────────────────────────────────────────────

class FakeEmailService:
    """Email service que registra los correos enviados en memoria."""

    def __init__(self) -> None:
        self.sent_count = 0
        self.last_recipient: str = ""
        self.last_link: str = ""

    async def send_password_reset(self, to_email: str, reset_link: str) -> None:
        self.sent_count += 1
        self.last_recipient = to_email
        self.last_link = reset_link


# ── CV parser fake ────────────────────────────────────────────────────────────

class FakeCvParser:
    """Parser de CV que devuelve un texto predefinido."""

    def __init__(self, extracted_text: str) -> None:
        self._text = extracted_text

    def extract_text(self, file_bytes: bytes, mime_type: str) -> str:
        return self._text


# ── Repositorio fake de vacantes ──────────────────────────────────────────────

class FakeVacanteRepository:
    """Repositorio en memoria para vacantes."""

    def __init__(self) -> None:
        self.vacantes: dict[UUID, "Vacante"] = {}

    async def create(
        self,
        empresa_id: UUID,
        titulo: str,
        descripcion: str,
        requisitos: list[str],
        ubicacion: str,
        categoria: str | None,
        salario_min: float | None,
        salario_max: float | None,
    ):
        from domain.entities.vacante import Vacante, VacanteEstado
        vacante = Vacante(
            id=uuid4(),
            empresa_id=empresa_id,
            titulo=titulo,
            descripcion=descripcion,
            requisitos=requisitos,
            ubicacion=ubicacion,
            estado=VacanteEstado.ACTIVA,
            creado_en=datetime.utcnow(),
            categoria=categoria,
            salario_min=salario_min,
            salario_max=salario_max,
        )
        self.vacantes[vacante.id] = vacante
        return vacante

    async def find_by_id(self, vacante_id: UUID):
        return self.vacantes.get(vacante_id)

    async def list_activas(
        self,
        ubicacion: str | None = None,
        categoria: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ):
        from domain.entities.vacante import VacanteEstado
        results = [
            v for v in self.vacantes.values()
            if v.estado == VacanteEstado.ACTIVA
            and (ubicacion is None or ubicacion.lower() in v.ubicacion.lower())
            and (categoria is None or (v.categoria and categoria.lower() in v.categoria.lower()))
        ]
        return results[offset: offset + limit]

    async def update(self, vacante_id: UUID, titulo: str, descripcion: str,
                     requisitos: list[str], ubicacion: str, categoria: str | None,
                     salario_min: float | None, salario_max: float | None):
        from dataclasses import replace
        v = self.vacantes[vacante_id]
        updated = replace(v, titulo=titulo, descripcion=descripcion, requisitos=requisitos,
                          ubicacion=ubicacion, categoria=categoria, salario_min=salario_min,
                          salario_max=salario_max)
        self.vacantes[vacante_id] = updated
        return updated

    async def change_estado(self, vacante_id: UUID, nuevo_estado):
        from dataclasses import replace
        v = self.vacantes[vacante_id]
        updated = replace(v, estado=nuevo_estado)
        self.vacantes[vacante_id] = updated
        return updated


# ── Repositorio fake de postulaciones ────────────────────────────────────────

class FakePostulacionRepository:
    """Repositorio en memoria para postulaciones."""

    def __init__(self) -> None:
        self.postulaciones: dict[UUID, "Postulacion"] = {}

    async def create(self, candidato_id: UUID, vacante_id: UUID):
        from domain.entities.postulacion import Postulacion, PostulacionEstado
        p = Postulacion(
            id=uuid4(),
            candidato_id=candidato_id,
            vacante_id=vacante_id,
            estado=PostulacionEstado.POSTULADO,
            fecha=datetime.utcnow(),
        )
        self.postulaciones[p.id] = p
        return p

    async def find_by_id(self, postulacion_id: UUID):
        return self.postulaciones.get(postulacion_id)

    async def find_by_candidato_and_vacante(self, candidato_id: UUID, vacante_id: UUID):
        return next(
            (p for p in self.postulaciones.values()
             if p.candidato_id == candidato_id and p.vacante_id == vacante_id),
            None,
        )

    async def list_by_candidato(self, candidato_id: UUID):
        return [p for p in self.postulaciones.values() if p.candidato_id == candidato_id]

    async def list_by_vacante(self, vacante_id: UUID):
        return [p for p in self.postulaciones.values() if p.vacante_id == vacante_id]

    async def change_estado(self, postulacion_id: UUID, nuevo_estado):
        from dataclasses import replace
        p = self.postulaciones[postulacion_id]
        updated = replace(p, estado=nuevo_estado)
        self.postulaciones[postulacion_id] = updated
        return updated
