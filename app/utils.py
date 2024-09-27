import functools
import time

from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from starlette.status import HTTP_400_BAD_REQUEST

def get_redis_client():
    from redis_client import redis_client
    return redis_client


# Base62 encoding function with adjustable length
def encode_base62(num: int, length: int = 6) -> str:
    """
    Encodes a number to Base62 with a specified minimum length.

    Args:
        num (int): The number to encode.
        length (int): The desired length of the Base62-encoded string. Defaults to 6.

    Returns:
        str: The Base62-encoded string, padded with '0' to the specified length if necessary.
    """
    BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if num == 0:
        return BASE62_ALPHABET[0].rjust(length, '0')
    
    base62 = []
    while num:
        num, rem = divmod(num, 62)
        base62.append(BASE62_ALPHABET[rem])
    
    encoded_str = ''.join(reversed(base62))
    
    # Pad the result with '0' to ensure the length is as specified
    return encoded_str.rjust(length, '0')


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

            redis_client = get_redis_client()

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
                status_code=HTTP_400_BAD_REQUEST,
                content={
                    "reason": "Invalid URL format",
                    "details": error['msg'],
                    "input": error['input'],
                    "success": False
                }
            )
    # Default response for other validation errors
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
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
class Redis_cache_handler:
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
        self.url_shortener_id = "url_shortener_id"
        self.redis_client = get_redis_client()

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
        return self.redis_client.hgetall(self.redis_key)

    def hset(self, mapping: dict = None) -> None:
        """
        Sets a hash value in Redis.

        Args:
            mapping (dict): The dictionary to store in the Redis hash.
        """
        if mapping:
            self.redis_client.hset(self.redis_key, mapping=mapping)

    def get(self) -> str:
        """
        Retrieves the value of a key from Redis.

        Returns:
            str: The value associated with the Redis key.
        """
        return self.redis_client.get(self.redis_key)

    def expire(self, ex: int) -> None:
        """
        Sets the expiration time for a Redis key.

        Args:
            ex (int): The expiration time in seconds.
        """
        self.redis_client.expire(self.redis_key, ex)

    def get_expiration_time(self) -> int:
        """
        Retrieves the time-to-live (TTL) for a Redis key.

        Returns:
            int: The TTL for the key in seconds.
        """
        return self.redis_client.ttl(self.redis_key)

    def set(self, value: str, ex: int = None, nx=None, key=None) -> None:
        """
        Sets a value in Redis with an optional expiration time.

        Args:
            value (str): The value to store.
            ex (int, optional): The expiration time in seconds.
        """
        key = key or self.redis_key
        self.redis_client.set(self.redis_key, value, ex=ex, nx=nx)

    def delete(self, key=None) -> None:
        """Deletes a key from Redis."""
        key = key or self.redis_key
        self.redis_client.delete(key)

    def incr(self) -> int:
        """Increments the value of a Redis key."""
        return self.redis_client.incr(self.redis_key)
    

class Table_id_handler:
    """
    A class to handle the generation of unique IDs for the URL shortener.
    """
    def __init__(self, this_talbe) -> None:
        self.this_table = this_talbe

    def get_new_id(self) -> int:
        """
        Checks if 'url_shortener_id' exists in Redis.
        - If it exists, increments and returns the value.
        - If it does not exist, retrieves the maximum ID from the database and uses a distributed lock to avoid race conditions.

        Returns:
            int: The incremented value of 'url_shortener_id'.
        """
        redis_handler = Redis_cache_handler("url_shortener_id", 'init')

        # TODO: Refactor redis_client or redis_handler to not only inherit from redis_client 
        # but also support additional syntactic sugar for easier usage and customization.
        redis_client = get_redis_client()

        # Check if 'url_shortener_id' already exists in Redis
        current_id = redis_handler.get()
        
        if current_id:
            # If the value exists in Redis, increment and return the new value
            new_id = redis_handler.incr()
            return new_id
        
        
        # If the value does not exist in Redis, use a Redis lock to avoid race conditions
        lock_acquired = redis_client.set("url_shortener_lock", value="1", nx=True, ex=5)  # Set a lock that expires after 5 seconds
        
        if lock_acquired:
            try:
                # After acquiring the lock, get the maximum ID from the database
                max_id = self.get_max_id_from_db()

                # Store the maximum ID from the database in Redis
                redis_handler.set(max_id, nx=True)
                
                # Increment and return the new value
                new_id = redis_handler.incr()
                return new_id
            finally:
                # Always release the lock
                redis_client.delete("url_shortener_lock")
        else:
            
            # If the lock is not available, wait for the lock to be released and then get the value
            while not current_id:
                time.sleep(0.1)  # Short wait
                print('waiting for current_id')
                current_id = redis_handler.get()
            
            # Increment and return the new value
            new_id = redis_handler.incr()
            return new_id


    def get_max_id_from_db(self) -> int:
        """
        Retrieves the maximum ID from the database.

        Returns:
            int: The maximum ID from the database.
        """
        # Assuming you have a session and URLMapping is the table
        from sqlalchemy.orm import sessionmaker
        from database import engine
        from sqlalchemy import func

        Session = sessionmaker(bind=engine)
        session = Session()

        max_id = session.query(func.max(self.this_table.id)).scalar() or 0
        session.close()
        return max_id