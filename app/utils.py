import functools
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from redis_client import redis_client


BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Base62 encoding function
def encode_base62(num: int) -> str:
    """
    Encodes a number to Base62.

    Args:
        num (int): The number to encode.

    Returns:
        str: The Base62-encoded string.
    """
    if num == 0:
        return BASE62_ALPHABET[0]
    base62 = []
    while num:
        num, rem = divmod(num, 62)
        base62.append(BASE62_ALPHABET[rem])
    return ''.join(reversed(base62))

# Rate-limiting decorator
def rate_limit(limit: int = 10, window: int = 60):
    """
    A decorator that limits the rate of function execution.

    Args:
        limit (int): Maximum number of requests allowed in the given window.
        window (int): Time window in seconds.

    Returns:
        Callable: A decorated function that is rate-limited.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            ip = request.client.host
            key = f"rate_limit:{ip}"

            # Increment request count
            current = redis_client.incr(key)

            # Set expiration time if this is the first request
            if current == 1:
                redis_client.expire(key, window)

            # Raise an error if the limit is exceeded
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


# Custom validation exception handler
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handles validation errors and returns a custom JSON response.

    Args:
        request (Request): The incoming request object.
        exc (RequestValidationError): The validation error.

    Returns:
        JSONResponse: A custom response indicating the validation failure.
    """
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

# Raise an HTTP error
def raise_http_error(status_code: int, reason: str, details: str) -> None:
    """
    Raises an HTTP error with a custom reason and details.

    Args:
        status_code (int): The HTTP status code.
        reason (str): The reason for the error.
        details (str): The details of the error.

    Raises:
        HTTPException: The raised HTTP exception.
    """
    raise HTTPException(
        status_code=status_code,
        detail={
            "reason": reason,
            "details": details,
            "success": False
        }
    )

# Redis cache handler class
class RedisCacheHandler:
    """
    A class to interact with Redis for caching URL data.
    """
    def __init__(self, url_cache_key: str, key_prefix: str = '') -> None:
        """
        Initialize Redis cache handler with a key prefix.

        Args:
            url_cache_key (str): The key for the URL cache.
            key_prefix (str): An optional prefix for the key.
        """
        self.url_cache_key = url_cache_key
        self.key_prefix = key_prefix

    @property
    def redis_key(self) -> str:
        """
        Generates the complete Redis key by appending the key prefix.

        Returns:
            str: The Redis key.
        """
        return f"{self.key_prefix}_{self.url_cache_key}"

    def hgetall(self) -> dict:
        """
        Retrieves all fields and values from a Redis hash.

        Returns:
            dict: The data stored in the Redis hash.
        """
        return redis_client.hgetall(self.redis_key)

    def hset(self, mapping: dict = None) -> None:
        """
        Sets a hash value in Redis.

        Args:
            mapping (dict): The dictionary to store in the Redis hash.
        """
        if mapping:
            redis_client.hset(self.redis_key, mapping=mapping)

    def get(self) -> str:
        """
        Retrieves the value of a key from Redis.

        Returns:
            str: The value associated with the Redis key.
        """
        return redis_client.get(self.redis_key)

    def expire(self, ex: int) -> None:
        """
        Sets the expiration time for a Redis key.

        Args:
            ex (int): The expiration time in seconds.
        """
        redis_client.expire(self.redis_key, ex)

    def get_expiration_time(self) -> int:
        """
        Retrieves the time-to-live (TTL) for a Redis key.

        Returns:
            int: The TTL for the key in seconds.
        """
        return redis_client.ttl(self.redis_key)

    def set(self, value: str, ex: int = '') -> None:
        """
        Sets a value in Redis with an optional expiration time.

        Args:
            value (str): The value to store.
            ex (int, optional): The expiration time in seconds.
        """
        redis_client.set(self.redis_key, value, ex=ex)
