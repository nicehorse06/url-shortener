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
from utils import encode_base62, rate_limit, get_db, raise_http_error, Redis_cache_handler
from models import URLMapping
from config import URL_VERSION, ONE_DAY_SECONDS, MAX_URL_LENGTH, URL_EXPIRATION_DATE



router = APIRouter(prefix=f"/urls/{URL_VERSION}", tags=["Short URLs"])


@router.post("/shorten", response_model=URLResponse, status_code=HTTP_201_CREATED)
@rate_limit(limit=10, window=60)  # 每分鐘最多10個請求
async def create_short_url(request: Request, request_data: URLRequest, db: Session = Depends(get_db)):
    original_url_str = str(request_data.original_url)  # Pydantic 的 AnyUrl 自動驗證 URL 格式

    # URL 長度檢查
    if len(original_url_str) > MAX_URL_LENGTH:
        raise_http_error(
            status_code=HTTP_400_BAD_REQUEST, 
            reason="URL is too long",
            details=f"The provided URL is {len(original_url_str)} characters long, but the maximum allowed length is {MAX_URL_LENGTH} characters.",
        )
    
    redis_handler = Redis_cache_handler(original_url_str, 'shorten')

    # check URL Redis cache
    return_data = redis_handler.hgetall()

    if not return_data.get("short_url"):
        # 查詢該 URL 是否已存在且未過期
        url_mapping = db.query(URLMapping).filter(
            URLMapping.original_url == original_url_str,
            URLMapping.expiration_date > datetime.now(timezone.utc)  # 檢查是否未過期
        ).first()

        if not url_mapping:
            # 如果 URL 格式正確且不存在重複，創建新的短網址映射
            try:
                short_url = encode_base62(db.query(URLMapping).count() + 1)  # 生成短網址

                # 創建新的 URL 映射
                url_mapping = URLMapping(
                    original_url=original_url_str,
                    short_url=short_url,
                    expiration_date=datetime.now(timezone.utc) + timedelta(days=URL_EXPIRATION_DATE)
                )
                db.add(url_mapping)
                db.commit()

            except Exception as e:
                db.rollback()  # 回滾操作避免錯誤的數據提交
                raise_http_error(
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR, 
                    reason="Short URL creating error.",
                    details=f"An error occurred while creating the short URL.",
                )
                
        return_data = url_mapping.set_shorten_original_url_cache(request)

    return URLResponse(
        short_url=return_data["short_url"],
        original_url=str(request_data.original_url),
        expiration_date=return_data["expiration_date"],
        success=True
    )


# 使用短網址進行重定向的 API
@router.get(f"/go/{{short_url}}")
@rate_limit(limit=10, window=60)  # 每分鐘最多10個請求
async def redirect_to_original(request: Request, short_url: str, db: Session = Depends(get_db)):
    redis_handler = Redis_cache_handler(short_url, 'redirect')

    # 優先從 Redis 中查找短網址對應的原始 URL
    original_url = redis_handler.get()

    if not original_url:
        # 查詢數據庫中的短網址記錄
        url_mapping = db.query(URLMapping).filter(URLMapping.short_url == short_url).first()
        
        if url_mapping:
            url_mapping.set_redirect_short_url_cache()

            original_url = url_mapping.original_url

        else:
            raise_http_error(
                status_code=HTTP_404_NOT_FOUND, 
                reason="Short URL not found",
                details=f"The short URL '{short_url}' does not exist. Please check the URL and try again.",
            )

    # 返回一個 302 重定向到 original_url
    return RedirectResponse(url=original_url)