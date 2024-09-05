import os
import redis

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


# Database and Redis configuration using environment variables
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./test.db')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# 配置 Redis
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

URL_VERSION = 'v1'

URL_EXPIRATION_DATE=30

# 24 * 60 * 60
ONE_DAY_SECONDS = 86400

MAX_URL_LENGTH = 2048


# 環境配置：根據環境變量選擇資料庫和 Redis
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./test.db')

# 配置 SQLAlchemy
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

