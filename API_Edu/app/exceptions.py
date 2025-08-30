from fastapi import HTTPException, status
from pydantic import ValidationError

class UserNotFoundException(HTTPException):
    def __init__(self, user_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пользователь с ID {user_id} не найден"
        )

class EmailAlreadyExistsException(HTTPException):
    def __init__(self, email: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Пользователь с email {email} уже существует"
        )

class DatabaseException(HTTPException):
    def __init__(self, detail: str = "Ошибка базы данных"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )

class ValidationException(HTTPException):
    def __init__(self, errors: list):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ошибка валидации данных",
            headers={"X-Error": "Validation"}
        )
        self.errors = errors