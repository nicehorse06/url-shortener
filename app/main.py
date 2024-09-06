from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from utils import validation_exception_handler
from database import init_db
from routers import short_url

# Initialize FastAPI application
app = FastAPI()

# Include the short_url router
app.include_router(short_url.router)

# Bind custom validation exception handler
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Initialize the database tables
init_db()

if __name__ == "__main__":
    import uvicorn
    # Start the FastAPI application
    uvicorn.run(app, host="0.0.0.0", port=8000)
