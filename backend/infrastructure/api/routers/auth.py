from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from application.use_cases.login_user import LoginUserCommand, LoginUserUseCase
from application.use_cases.register_candidate import (
    RegisterCandidateCommand,
    RegisterCandidateUseCase,
)
from application.use_cases.register_company import RegisterCompanyCommand, RegisterCompanyUseCase
from domain.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError
from infrastructure.adapters.persistence.database import get_session
from infrastructure.adapters.persistence.user_repository import SqlAlchemyUserRepository
from infrastructure.adapters.security import JwtTokenService, PasslibPasswordHasher
from infrastructure.api.schemas.auth import (
    CandidateRegisterRequest,
    CandidateRegisterResponse,
    CompanyRegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/registro/candidato",
    response_model=CandidateRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_candidate(
    request: CandidateRegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> CandidateRegisterResponse:
    users = SqlAlchemyUserRepository(session)
    use_case = RegisterCandidateUseCase(users, PasslibPasswordHasher())

    try:
        profile = await use_case.execute(
            RegisterCandidateCommand(
                email=request.email,
                password=request.password,
                full_name=request.full_name,
                skills=request.skills,
                experience_years=request.experience_years,
                location=request.location,
                education=request.education,
            )
        )
        await session.commit()
    except (EmailAlreadyRegisteredError, IntegrityError) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from exc

    return CandidateRegisterResponse(
        id=profile.id,
        user_id=profile.user_id,
        full_name=profile.full_name,
        skills=profile.skills,
        experience_years=profile.experience_years,
        location=profile.location,
        education=profile.education,
    )


@router.post(
    "/registro/empresa",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_company(
    request: CompanyRegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> UserResponse:
    users = SqlAlchemyUserRepository(session)
    use_case = RegisterCompanyUseCase(users, PasslibPasswordHasher())

    try:
        user = await use_case.execute(
            RegisterCompanyCommand(email=request.email, password=request.password)
        )
        await session.commit()
    except (EmailAlreadyRegisteredError, IntegrityError) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from exc

    return UserResponse(id=user.id, email=user.email, role=user.role, created_at=user.created_at)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    users = SqlAlchemyUserRepository(session)
    use_case = LoginUserUseCase(users, PasslibPasswordHasher(), JwtTokenService())

    try:
        result = await use_case.execute(LoginUserCommand(email=request.email, password=request.password))
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc

    return TokenResponse(access_token=result.access_token, token_type=result.token_type)

