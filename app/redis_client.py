import redis
from config import REDIS_URL

# Redis client configuration
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
