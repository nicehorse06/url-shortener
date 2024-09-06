from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR
)
from sqlalchemy.orm import Session
from api_schemas import URLRequest, URLResponse
from utils import encode_base62, rate_limit, raise_http_error, Redis_cache_handler
from database import get_db
from models import URLMapping
from config import URL_VERSION, MAX_URL_LENGTH, URL_EXPIRATION_DATE

router = APIRouter(prefix=f"/urls/{URL_VERSION}", tags=["Short URLs"])


@router.post("/shorten", response_model=URLResponse, status_code=HTTP_201_CREATED)
@rate_limit(limit=10, window=60)  # Rate limit to 10 requests per minute
async def create_short_url(
    request: Request, 
    request_data: URLRequest, 
    db: Session = Depends(get_db)
) -> URLResponse:
    """
    Shorten a given original URL and return the shortened URL.

    Args:
        request (Request): FastAPI request object.
        request_data (URLRequest): Request body containing the original URL.
        db (Session): SQLAlchemy session for database access.

    Returns:
        URLResponse: A response object with the shortened URL, original URL, and expiration date.
    """
    original_url_str = str(request_data.original_url)

    # Check if the URL exceeds the maximum length allowed
    if len(original_url_str) > MAX_URL_LENGTH:
        raise_http_error(
            status_code=HTTP_400_BAD_REQUEST,
            reason="URL is too long",
            details=f"The provided URL is {len(original_url_str)} characters long, but the maximum allowed length is {MAX_URL_LENGTH} characters.",
        )
    
    redis_handler = Redis_cache_handler(original_url_str, 'shorten')

    # Check if the URL is already cached in Redis
    return_data = redis_handler.hgetall()

    if not return_data.get("short_url"):
        # Query the database for an existing URL that hasn't expired
        url_mapping = db.query(URLMapping).filter(
            URLMapping.original_url == original_url_str,
            URLMapping.expiration_date > datetime.now(timezone.utc)
        ).first()

        if not url_mapping:
            # Create a new short URL if none exists
            try:
                short_url = encode_base62(db.query(URLMapping).count() + 1)

                # Create a new URL mapping in the database
                url_mapping = URLMapping(
                    original_url=original_url_str,
                    short_url=short_url,
                    expiration_date=datetime.now(timezone.utc) + timedelta(days=URL_EXPIRATION_DATE)
                )
                db.add(url_mapping)
                db.commit()

            except Exception:
                db.rollback()
                raise_http_error(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    reason="Short URL creation error.",
                    details="An error occurred while creating the short URL.",
                )
                
        # Cache the newly created URL mapping in Redis
        return_data = url_mapping.set_shorten_original_url_cache(request)

    return URLResponse(
        short_url=return_data["short_url"],
        original_url=str(request_data.original_url),
        expiration_date=return_data["expiration_date"],
        success=True
    )


@router.get(f"/go/{{short_url}}")
@rate_limit(limit=10, window=60)  # Rate limit to 10 requests per minute
async def redirect_to_original(
    request: Request, 
    short_url: str, 
    db: Session = Depends(get_db)
) -> RedirectResponse:
    """
    Redirect a short URL to its corresponding original URL.

    Args:
        request (Request): FastAPI request object.
        short_url (str): The shortened URL to be redirected.
        db (Session): SQLAlchemy session for database access.

    Returns:
        RedirectResponse: A 302 redirect response to the original URL.
    """
    redis_handler = Redis_cache_handler(short_url, 'redirect')

    # Check if the original URL is cached in Redis
    original_url = redis_handler.get()

    if not original_url:
        # Query the database for the original URL using the short URL
        url_mapping = db.query(URLMapping).filter(URLMapping.short_url == short_url).first()
        
        if url_mapping:
            # Cache the URL in Redis for future lookups
            url_mapping.set_redirect_short_url_cache()
            original_url = url_mapping.original_url

        else:
            raise_http_error(
                status_code=HTTP_404_NOT_FOUND,
                reason="Short URL not found",
                details=f"The short URL pattern '{short_url}' does not exist. Please check the URL and try again.",
            )

    return RedirectResponse(url=original_url)
