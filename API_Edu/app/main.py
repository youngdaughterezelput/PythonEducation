from fastapi import FastAPI, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import ValidationError
import logging

from app.database import get_db, init_db
from app.repositories import UserRepository
from app.services import UserService
from app.schemas import UserCreate, UserResponse, ErrorResponse, ValidationErrorResponse
from app.exceptions import (
    UserNotFoundException, 
    EmailAlreadyExistsException, 
    DatabaseException,
    ValidationException
)
from app.database import init_db

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация приложения
app = FastAPI(
    title="User Management API",
    description="API для управления пользователями",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Users",
            "description": "Операции с пользователями"
        }
    ]
)

# Инициализация базы данных
@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("Application started and database initialized")

# Глобальные обработчики исключений
@app.exception_handler(UserNotFoundException)
async def user_not_found_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_type": "not_found"}
    )

@app.exception_handler(EmailAlreadyExistsException)
async def email_exists_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_type": "conflict"}
    )

@app.exception_handler(DatabaseException)
async def database_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error_type": "database_error"}
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Ошибка валидации данных",
            "error_type": "validation_error",
            "errors": exc.errors()
        }
    )

# Зависимости
def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

def get_user_service(user_repository: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(user_repository)

# Эндпоинты
@app.post(
    "/users/", 
    response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Bad request - email already exists", "model": ErrorResponse},
        422: {"description": "Validation error - invalid input data", "model": ValidationErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    },
    tags=["Users"]
)
def create_user(
    user: UserCreate, 
    user_service: UserService = Depends(get_user_service)
):
    """
    Create a new user with the following information:
    - **name**: must be between 2 and 50 characters, letters and spaces only
    - **email**: must be a valid email format
    - **age**: must be between 1 and 120
    """
    return user_service.create_user(user)

@app.get(
    "/users/", 
    response_model=list[UserResponse],
    responses={
        200: {"description": "List of users retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    },
    tags=["Users"]
)
def read_users(
    skip: int = 0, 
    limit: int = 100, 
    user_service: UserService = Depends(get_user_service)
):
    """
    Retrieve a list of users with pagination:
    - **skip**: number of records to skip (default 0)
    - **limit**: maximum number of records to return (default 100, max 1000)
    """
    return user_service.get_all_users(skip, min(limit, 1000))

@app.get(
    "/users/{user_id}", 
    response_model=UserResponse,
    responses={
        200: {"description": "User retrieved successfully"},
        404: {"description": "User not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    },
    tags=["Users"]
)
def read_user(
    user_id: int, 
    user_service: UserService = Depends(get_user_service)
):
    """
    Retrieve a specific user by ID
    """
    return user_service.get_user(user_id)

@app.put(
    "/users/{user_id}", 
    response_model=UserResponse,
    responses={
        200: {"description": "User updated successfully"},
        400: {"description": "Bad request - email already exists", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        422: {"description": "Validation error - invalid input data", "model": ValidationErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    },
    tags=["Users"]
)
def update_user(
    user_id: int, 
    user: UserCreate, 
    user_service: UserService = Depends(get_user_service)
):
    """
    Update an existing user
    """
    return user_service.update_user(user_id, user)

@app.delete(
    "/users/{user_id}",
    responses={
        200: {"description": "User deleted successfully"},
        404: {"description": "User not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    },
    tags=["Users"]
)
def delete_user(
    user_id: int, 
    user_service: UserService = Depends(get_user_service)
):
    """
    Delete a user by ID
    """
    user_service.delete_user(user_id)
    return {"message": "Пользователь успешно удален"}