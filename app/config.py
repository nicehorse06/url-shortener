import os

# Database and Redis configuration using environment variables
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./test.db')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Configuration constants
URL_VERSION = 'v1'
URL_EXPIRATION_DATE = 30  # Default URL expiration time in days
ONE_DAY_SECONDS = 86400  # 24 hours in seconds
MAX_URL_LENGTH = 2048  # Maximum URL length allowed

