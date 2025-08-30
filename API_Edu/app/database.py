from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    try:
        # Удаляем все таблицы (если есть)
        Base.metadata.drop_all(bind=engine)
        # Создаём таблицы заново
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise