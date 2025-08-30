from sqlalchemy.orm import Session
from app.models import UserDB
from app.exceptions import UserNotFoundException, EmailAlreadyExistsException, DatabaseException
from app.schemas import UserCreate
import logging

logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_user(self, user_id: int) -> UserDB:
        try:
            user = self.db.query(UserDB).filter(UserDB.id == user_id).first()
            if not user:
                raise UserNotFoundException(user_id)
            return user
        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Database error in get_user: {e}")
            raise DatabaseException("Ошибка при получении пользователя")
    
    def get_all_users(self, skip: int = 0, limit: int = 100) -> list[UserDB]:
        try:
            return self.db.query(UserDB).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Database error in get_all_users: {e}")
            raise DatabaseException("Ошибка при получении списка пользователей")
    
    def create_user(self, user: UserCreate) -> UserDB:
        try:
            # Проверяем, существует ли пользователь с таким email
            existing_user = self.db.query(UserDB).filter(UserDB.email == user.email).first()
            if existing_user:
                raise EmailAlreadyExistsException(user.email)
            
            # Создаем нового пользователя
            db_user = UserDB(**user.model_dump())
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            return db_user
        except EmailAlreadyExistsException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Database error in create_user: {e}")
            raise DatabaseException("Ошибка при создании пользователя")
    
    def update_user(self, user_id: int, user: UserCreate) -> UserDB:
        try:
            db_user = self.get_user(user_id)
            
            # Проверяем, не занят ли email другим пользователем
            if user.email != db_user.email:
                existing_user = self.db.query(UserDB).filter(UserDB.email == user.email).first()
                if existing_user:
                    raise EmailAlreadyExistsException(user.email)
            
            # Обновляем данные пользователя
            for field, value in user.model_dump().items():
                setattr(db_user, field, value)
            
            self.db.commit()
            self.db.refresh(db_user)
            return db_user
        except (UserNotFoundException, EmailAlreadyExistsException):
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Database error in update_user: {e}")
            raise DatabaseException("Ошибка при обновлении пользователя")
    
    def delete_user(self, user_id: int) -> None:
        try:
            db_user = self.get_user(user_id)
            self.db.delete(db_user)
            self.db.commit()
        except UserNotFoundException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Database error in delete_user: {e}")
            raise DatabaseException("Ошибка при удалении пользователя")