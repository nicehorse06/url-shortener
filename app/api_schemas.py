from pydantic import BaseModel, AnyUrl, field_validator
from datetime import datetime


class URLRequest(BaseModel):
    """Pydantic model for handling URL shortening request."""
    original_url: AnyUrl  # Validates and accepts the original URL


class URLResponse(BaseModel):
    """Pydantic model for URL shortening response."""
    short_url: str  # The generated short URL
    expiration_date: str  # Display the expiration date as a string (date only)
    success: bool  # Indicates whether the operation was successful
    reason: str = None  # Reason for failure, if any
    original_url: str  # The original URL

    @field_validator('expiration_date', mode='before')
    def format_expiration_date(cls, v: str | datetime) -> str:
        """
        Validator to format the expiration date.
        If the value is a datetime object, it returns only the date part in ISO format.

        Args:
            v (str | datetime): The value to validate (either a string or datetime object).

        Returns:
            str: The formatted date string.
        """
        if isinstance(v, datetime):
            return v.date().isoformat()
        return v
