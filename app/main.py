import redis
import os
from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel, AnyUrl
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
                raise HTTPException(status_code=429, detail="Rate limit exceeded")

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# 創建短網址的 API
@app.post("/shorten", response_model=URLResponse)
@rate_limit(limit=10, window=60)  # 每分鐘最多10個請求
async def create_short_url(request: Request, request_data: URLRequest, db: Session = Depends(get_db)):
    original_url_str = str(request_data.original_url)  # 將 Pydantic 的 AnyUrl 轉換為字符串

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

    return URLResponse(
        short_url=short_url,
        expiration_date=url_mapping.expiration_date,
        success=True
    )

# 使用短網址進行重定向的 API
@app.get("/{short_url}")
@rate_limit(limit=10, window=60)  # 每分鐘最多10個請求
async def redirect_to_original(request: Request, short_url: str, db: Session = Depends(get_db)):
    original_url = redis_client.get(short_url)

    if not original_url:
        url_mapping = db.query(URLMapping).filter(URLMapping.short_url == short_url).first()
        if url_mapping:
            original_url = url_mapping.original_url
            ex = int((url_mapping.expiration_date - datetime.now(timezone.utc)).total_seconds())
            redis_client.set(short_url, original_url, ex=ex)
        else:
            raise HTTPException(status_code=404, detail="Short URL not found")

    return {"original_url": original_url}

if __name__ == "__main__":
    import uvicorn
    # 啟動 FastAPI 應用
    uvicorn.run(app, host="0.0.0.0", port=8000)
