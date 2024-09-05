from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from models import URLMapping
from api_schemas import URLRequest

# Create or retrieve an existing short URL
def create_short_url(db: Session, request: URLRequest, base_url: str, short_url: str) -> URLMapping:
    existing_url = db.query(URLMapping).filter(
        URLMapping.original_url == str(request.original_url),
        URLMapping.expiration_date > datetime.now(timezone.utc)
    ).first()

    if existing_url:
        return existing_url

    # Create a new short URL mapping
    expiration_date = datetime.now(timezone.utc) + timedelta(days=30)
    url_mapping = URLMapping(original_url=str(request.original_url), short_url=short_url, expiration_date=expiration_date)
    db.add(url_mapping)
    db.commit()
    db.refresh(url_mapping)

    return url_mapping
