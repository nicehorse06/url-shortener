from sqlalchemy import Column, String, Integer, DateTime
from config import Base, ONE_DAY_SECONDS
from datetime import datetime, timezone
from starlette.status import HTTP_410_GONE
from utils import raise_http_error, Redis_cache_handler
from fastapi import Request


# Define the database model for URL mappings
class URLMapping(Base):
    __tablename__ = "url_mappings"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    original_url = Column(String, nullable=False)
    short_url = Column(String, unique=True, index=True)
    expiration_date = Column(DateTime, nullable=False)

    def real_short_url(self, request: Request) -> str:
        """
        Generates a full short URL based on the request object and short_url pattern.

        Args:
            request (Request): The FastAPI request object.

        Returns:
            str: The complete short URL.
        """
        from config import URL_VERSION
        this_port = f':{request.url.port}' if request.url.port else ''
        return f"{request.url.scheme}://{request.url.hostname}{this_port}/urls/{URL_VERSION}/go/{self.short_url}"
    
    def check_if_expired(self) -> None:
        """
        Checks if the URL is expired and raises an HTTP error if so.

        Raises:
            HTTPException: If the URL has expired.
        """
        # Ensure expiration_date is a timezone-aware datetime object
        if self.expiration_date.tzinfo is None:
            # If expiration_date is naive, convert it to UTC
            self.expiration_date = self.expiration_date.replace(tzinfo=timezone.utc)
        
        if self.expiration_date < datetime.now(timezone.utc):
            raise_http_error(
                status_code=HTTP_410_GONE,
                reason="Short URL expired",
                details=f"The short URL '{self.short_url}' has expired and is no longer accessible."
            )

    def set_shorten_original_url_cache(self, request: Request) -> dict:
        """
        Caches the original URL and expiration date in Redis.

        Args:
            request (Request): The FastAPI request object.

        Returns:
            dict: A dictionary containing the cached short URL and expiration date.
        """
        redis_handler = Redis_cache_handler(self.original_url, 'shorten')

        expiration_date_aware = self.expiration_date.replace(tzinfo=timezone.utc)
        ex = int((expiration_date_aware - datetime.now(timezone.utc)).total_seconds())

        cache_data = {
            "short_url": self.real_short_url(request),
            "expiration_date": self.expiration_date.isoformat()
        }

        # Use Redis hash to store short URL and expiration date
        redis_handler.hset(cache_data)

        # Set expiration time for the key
        redis_handler.expire(ex)

        return cache_data

    def set_redirect_short_url_cache(self) -> None:
        """
        Caches the original URL and expiration date in Redis for redirect purposes.
        """
        # Check if the URL has expired
        self.check_if_expired()

        redis_handler = Redis_cache_handler(self.short_url, 'redirect')

        # Calculate the expiration time
        expiration_date_aware = self.expiration_date.replace(tzinfo=timezone.utc)
        seconds_until_expiration = int((expiration_date_aware - datetime.now(timezone.utc)).total_seconds())

        # Set expiration time as the smaller value between expiration date and one day
        redis_expiration_time = min(seconds_until_expiration, ONE_DAY_SECONDS)

        # Cache the original URL and set expiration in Redis
        redis_handler.set(self.original_url, ex=redis_expiration_time)
