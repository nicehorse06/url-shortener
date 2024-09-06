# URL Shortener Project

## Introduction

This is a URL Shortener application built using FastAPI, SQLAlchemy, Redis, and PostgreSQL/SQLite. The application provides API endpoints for generating short URLs and redirecting them to their original URLs. It leverages Redis for caching and rate limiting, and uses SQLAlchemy as the ORM for interacting with a relational database.

## Features Implemented

- URL shortening: Converts long URLs into short URLs and stores them in the database.
- Redirection: Redirects short URLs to the original long URLs.
- URL expiration: Each short URL has a default expiration period of 30 days.
- Caching: Redis is used to cache the URL mappings and reduce database lookups.h
- Rate limiting: Ensures that clients cannot abuse the API by limiting requests per IP.
- Environment-specific configurations: The app can run locally with SQLite or in Docker with PostgreSQL and Redis.
- Automatic database initialization in Docker Compose.

## Available APIs

### 1. Shorten URL
- **Endpoint**: `/urls/v1/shorten`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "original_url": "https://example.com"
  }
  ```
- **Response**:
  ```json
  {
    "short_url": "http://localhost:8000/urls/v1/go/abc123",
    "expiration_date": "2024-12-31",
    "success": true,
    "original_url": "https://example.com"
  }
  ```

### 2. Redirect URL
- **Endpoint**: `/urls/v1/go/{short_url}`
- **Method**: `GET`
- **Response**: Redirects the user to the original URL.

## How to Start the Project

### Local Development
1. Clone the repository.
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the FastAPI app:
   ```bash
   uvicorn app.main:app --reload
   ```
4. By default, the app will run on `http://localhost:8000`.

### Docker Compose
1. Ensure Docker is installed and running.
2. Run the application using Docker Compose:
   ```bash
   docker compose up --build
   ```
3. The app will be accessible on `http://localhost:8000` and automatically connect to PostgreSQL and Redis containers.

### Viewing FastAPI Swagger Documentation
Once the app is running, you can view the automatically generated API documentation by navigating to:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

