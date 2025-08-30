from app.repositories import UserRepository
from app.schemas import UserCreate
from app.exceptions import DatabaseException
import logging

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
    
    def get_user(self, user_id: int):
        return self.user_repository.get_user(user_id)
    
    def get_all_users(self, skip: int = 0, limit: int = 100):
        return self.user_repository.get_all_users(skip, limit)
    
    def create_user(self, user: UserCreate):
        return self.user_repository.create_user(user)
    
    def update_user(self, user_id: int, user: UserCreate):
        return self.user_repository.update_user(user_id, user)
    
    def delete_user(self, user_id: int):
        return self.user_repository.delete_user(user_id)