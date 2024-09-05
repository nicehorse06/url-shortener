from sqlalchemy import Column, String, Integer, DateTime
from config import engine, Base, ONE_DAY_SECONDS
from datetime import datetime, timezone
from starlette.status import HTTP_410_GONE
from utils import raise_http_error, Redis_cache_handler

# 定義數據庫模型
class URLMapping(Base):
    __tablename__ = "url_mappings"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    original_url = Column(String, nullable=False)
    short_url = Column(String, unique=True, index=True)
    expiration_date = Column(DateTime, nullable=False)

    def real_short_url(self, request):
        """Generates a full short URL based on the request object and short_url pattern."""
        from config import URL_VERSION
        this_port = f':{request.url.port}' if request.url.port else ''
        return f"{request.url.scheme}://{request.url.hostname}{this_port}/urls/{URL_VERSION}/go/{self.short_url}"
    
    def check_if_expired(self):
        """Checks if the URL is expired and raises an error if so."""
        # 確保 expiration_date 是一個具有時區信息的 offset-aware datetime
        if self.expiration_date.tzinfo is None:
            # 如果 expiration_date 沒有時區信息，將其設置為 UTC 時區
            self.expiration_date = self.expiration_date.replace(tzinfo=timezone.utc)
        
        if self.expiration_date < datetime.now(timezone.utc):
            raise_http_error(
                status_code=HTTP_410_GONE,
                reason="Short URL expired",
                details=f"The short URL '{self.short_url}' has expired and is no longer accessible."
            )

    def set_shorten_original_url_cache(self, request):

        """Caches the original URL and expiration date in Redis."""
        redis_handler = Redis_cache_handler(self.original_url, 'shorten')

        expiration_date_aware = self.expiration_date.replace(tzinfo=timezone.utc)
        ex = int((expiration_date_aware - datetime.now(timezone.utc)).total_seconds())

        cache_data = {
            "short_url": self.real_short_url(request),
            "expiration_date": self.expiration_date.isoformat()
        }

        # Use Redis hash to store short URL and expiration date.
        redis_handler.hset(cache_data)

        # Set expiration time for the key.
        redis_handler.expire(ex)

        return cache_data


    def set_redirect_short_url_cache(self):
    
        # 檢查是否已過期
        self.check_if_expired()

        """Caches the original URL and expiration date in Redis."""
        redis_handler = Redis_cache_handler(self.short_url, 'redirect')

        # 計算過期時間
        expiration_date_aware = self.expiration_date.replace(tzinfo=timezone.utc)
        seconds_until_expiration = int((expiration_date_aware - datetime.now(timezone.utc)).total_seconds())

        # 設置過期時間為兩者中較短的那一個
        redis_expiration_time = min(seconds_until_expiration, ONE_DAY_SECONDS)

        # 將短網址與原始 URL 存入 Redis 並設置過期時間
        redis_handler.set(self.original_url, ex=redis_expiration_time)

Base.metadata.create_all(bind=engine)