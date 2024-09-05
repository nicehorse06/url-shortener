import functools
from datetime import datetime, timezone

from fastapi import Request, HTTPException, HTTPException
from config import redis_client, SessionLocal
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Base62 encoding function
def encode_base62(num: int) -> str:
    if num == 0:
        return BASE62_ALPHABET[0]
    base62 = []
    while num:
        num, rem = divmod(num, 62)
        base62.append(BASE62_ALPHABET[rem])
    return ''.join(reversed(base62))


# 速率限制裝飾器
def rate_limit(limit: int = 10, window: int = 60):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            ip = request.client.host
            key = f"rate_limit:{ip}"

            # 增加請求計數
            current = redis_client.incr(key)

            # 如果是第一次設置，設置過期時間
            if current == 1:
                redis_client.expire(key, window)

            # 如果超過限制，拋出異常
            if current > limit:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "reason": "Rate limit exceeded",
                        "details": f"You have exceeded the limit of {limit} requests per {window} seconds. Please wait before sending more requests.",
                        "success": False
                    }
                )

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# 依賴注入：每次請求時獲取數據庫 session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Extract error details
    error_details = exc.errors()
    for error in error_details:
        if error['loc'] == ('body', 'original_url'):
            # Custom response for original_url validation errors
            return JSONResponse(
                status_code=400,
                content={
                    "reason": "Invalid URL format",
                    "details": error['msg'],
                    "input": error['input'],
                    "success": False
                }
            )
    # Default response for other validation errors
    return JSONResponse(
        status_code=400,
        content={
            "reason": "Validation error",
            "details": error_details,
            "success": False
        }
    )

def raise_http_error(status_code: int, reason: str, details: str):
    raise HTTPException(
        status_code=status_code,
        detail={
            "reason": reason,
            "details": details,
            "success": False
        }
    )

class Redis_cache_handler:
    def __init__(self, url_cahce_key, key_prefix='') -> None:
        self.url_cahce_key = url_cahce_key
        self.key_prefix = key_prefix

    @property
    def redis_key(self):
        return f"{self.key_prefix}_{self.url_cahce_key}"

    def hgetall(self):
        """Retrieve all fields and values for the given key."""
        return redis_client.hgetall(self.redis_key)

    def hset(self, mapping=None):
        if mapping :
            redis_client.hset(self.redis_key, mapping=mapping)

    def get(self):
        """Retrieve a specific key from Redis."""
        return redis_client.get(self.redis_key)
    
    def expire(self, ex):
        redis_client.expire(self.redis_key, ex)

    def get_expiration_time(self):
        """Retrieve the TTL (time-to-live) for a given key."""
        return redis_client.ttl(self.redis_key)
    
    def set(self, value, ex=''):
        """Set a key-value pair with an optional expiration time in Redis."""
        redis_client.set(self.redis_key, value, ex=ex)
    