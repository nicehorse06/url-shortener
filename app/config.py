import os
import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database and Redis configuration using environment variables
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./test.db')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Redis client configuration
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Configuration constants
URL_VERSION = 'v1'
URL_EXPIRATION_DATE = 30  # Default URL expiration time in days
ONE_DAY_SECONDS = 86400  # 24 hours in seconds
MAX_URL_LENGTH = 2048  # Maximum URL length allowed

# Database configuration: check for SQLite and configure engine accordingly
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

# Database session and model base configuration
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
