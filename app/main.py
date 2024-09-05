from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from utils import validation_exception_handler
from routers import short_url

# 初始化 FastAPI 應用
app = FastAPI()

app.include_router(short_url.router)

# 綁定自定義的錯誤處理器
app.add_exception_handler(RequestValidationError, validation_exception_handler)


if __name__ == "__main__":
    import uvicorn
    # 啟動 FastAPI 應用
    uvicorn.run(app, host="0.0.0.0", port=8000)
