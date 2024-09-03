import redis
import os

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse

from pydantic import BaseModel, AnyUrl, ValidationError
from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from datetime import datetime, timedelta, timezone
import functools

# 初始化 FastAPI 應用
app = FastAPI()

# 環境配置：根據環境變量選擇資料庫和 Redis
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./test.db')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# 配置 SQLAlchemy
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 配置 Redis
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Base62 字符集，用於生成短網址
BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

# url version
url_version = 'v1'

# 自定義錯誤處理器
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # 尋找所有的錯誤訊息
    error_details = exc.errors()
    for error in error_details:
        if error['loc'] == ('body', 'original_url'):
            # 返回更詳細的錯誤信息，說明為何 URL 格式無效
            return JSONResponse(
                status_code=400,
                content={
                    "reason": "Invalid URL format",
                    "details": error['msg'],  # 包含更詳細的錯誤描述
                    "input": error['input'],  # 返回用戶輸入的無效 URL
                    "success": False
                }
            )
    # 對於其他驗證錯誤，返回默認的錯誤訊息
    return JSONResponse(
        status_code=400,
        content={
            "reason": "Validation error",
            "details": error_details,  # 返回所有驗證錯誤的詳細信息
            "success": False
        }
    )


# 定義數據庫模型
class URLMapping(Base):
    __tablename__ = "url_mappings"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    original_url = Column(String, nullable=False)
    short_url = Column(String, unique=True, index=True)
    expiration_date = Column(DateTime, nullable=False)

Base.metadata.create_all(bind=engine)

# 定義 Pydantic 模型，用於請求和響應數據結構
class URLRequest(BaseModel):
    original_url: AnyUrl  # 接收並驗證原始 URL

class URLResponse(BaseModel):
    short_url: str  # 返回生成的短網址
    expiration_date: datetime  # 返回短網址的過期時間
    success: bool  # 操作是否成功
    reason: str = None  # 如果失敗，返回失敗原因

# 依賴注入：每次請求時獲取數據庫 session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Base62 編碼：將數字 ID 轉換為 Base62 字符串
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


@app.post(f"/urls/{url_version}/shorten", response_model=URLResponse, status_code=201)
@rate_limit(limit=10, window=60)  # 每分鐘最多10個請求
async def create_short_url(request: Request, request_data: URLRequest, db: Session = Depends(get_db)):
    original_url_str = str(request_data.original_url)  # Pydantic 的 AnyUrl 自動驗證 URL 格式

    # URL 長度檢查
    if len(original_url_str) > 2048:
        return JSONResponse(
            status_code=400,
            content={
                "reason": "URL is too long",
                "details": f"The provided URL is {len(original_url_str)} characters long, but the maximum allowed length is 2048 characters.",
                "success": False
            }
        )

    # 查詢該 URL 是否已存在
    existing_url = db.query(URLMapping).filter(URLMapping.original_url == original_url_str).first()
    if existing_url:
        full_short_url = f"{request.url.scheme}://{request.url.hostname}:{request.url.port}/urls/{url_version}/go/{existing_url.short_url}"
        return URLResponse(
            short_url=full_short_url,
            expiration_date=existing_url.expiration_date,
            success=True
        )

    # 如果 URL 格式正確且不存在重複，創建新的短網址映射
    url_mapping = URLMapping(
        original_url=original_url_str,
        expiration_date=datetime.now(timezone.utc) + timedelta(days=30)
    )
    db.add(url_mapping)
    db.commit()
    db.refresh(url_mapping)

    short_url = encode_base62(url_mapping.id)
    url_mapping.short_url = short_url
    db.commit()

    expiration_date_aware = url_mapping.expiration_date.replace(tzinfo=timezone.utc)
    ex = int((expiration_date_aware - datetime.now(timezone.utc)).total_seconds())

    redis_client.set(short_url, original_url_str, ex=ex)

    # 根據當前運行環境生成完整的短網址
    this_port = f':{request.url.port}' if request.url.port else ''
    full_short_url = f"{request.url.scheme}://{request.url.hostname}{this_port}/urls/{url_version}/go/{short_url}"

    return URLResponse(
        short_url=full_short_url,
        expiration_date=url_mapping.expiration_date,
        success=True
    )


# 使用短網址進行重定向的 API
@app.get(f"/urls/{url_version}/go/{{short_url}}")
@rate_limit(limit=10, window=60)  # 每分鐘最多10個請求
async def redirect_to_original(request: Request, short_url: str, db: Session = Depends(get_db)):
    original_url = redis_client.get(short_url)

    if not original_url:
        url_mapping = db.query(URLMapping).filter(URLMapping.short_url == short_url).first()
        if url_mapping:
            original_url = url_mapping.original_url
            # 確保 expiration_date 是一個具有 UTC 時區的 datetime 對象
            expiration_date_aware = url_mapping.expiration_date.replace(tzinfo=timezone.utc)
            ex = int((expiration_date_aware - datetime.now(timezone.utc)).total_seconds())
            redis_client.set(short_url, original_url, ex=ex)
        else:
            raise HTTPException(
                status_code=404,
                detail={
                    "reason": "Short URL not found",
                    "details": f"The short URL '{short_url}' does not exist or has expired. Please check the URL and try again.",
                    "success": False
                }
            )

    # 生成當天的 Redis key，例如：usage:abc123:20240901
    today = datetime.now().strftime('%Y%m%d')
    usage_key = f"usage:{short_url}:{today}"

    # 增加該短網址的當天使用次數
    redis_client.incr(usage_key)

    # 設置該 key 的過期時間為 24 小時（如果尚未設置過期時間）
    if redis_client.ttl(usage_key) == -1:
        redis_client.expire(usage_key, 86400)  # 86400 秒即 24 小時

    # 返回一個 302 重定向到 original_url
    return RedirectResponse(url=original_url)

if __name__ == "__main__":
    import uvicorn
    # 啟動 FastAPI 應用
    uvicorn.run(app, host="0.0.0.0", port=8000)
