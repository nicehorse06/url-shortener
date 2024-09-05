from pydantic import BaseModel, AnyUrl, field_validator
from datetime import datetime

# 定義 Pydantic 模型，用於請求和響應數據結構
class URLRequest(BaseModel):
    original_url: AnyUrl  # 接收並驗證原始 URL

class URLResponse(BaseModel):
    short_url: str  # 返回生成的短網址
    expiration_date: str  # 修改為只顯示日期的字符串
    success: bool  # 操作是否成功
    reason: str = None  # 如果失敗，返回失敗原因
    original_url: str

    @field_validator('expiration_date', mode='before')
    def format_expiration_date(cls, v):
        # 如果 v 是 datetime 對象，則只取日期部分
        if isinstance(v, datetime):
            return v.date().isoformat()
        return v