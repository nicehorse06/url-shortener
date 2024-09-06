# URL Shortener Project

## Introduction

This is a URL Shortener application built using FastAPI, SQLAlchemy, Redis, and PostgreSQL/SQLite. The application provides API endpoints for generating short URLs and redirecting them to their original URLs. It leverages Redis for caching and rate limiting, and uses SQLAlchemy as the ORM for interacting with a relational database.

## Features

1. **URL Shortening**: Converts long URLs into shortened versions.
2. **URL Redirection**: Redirects users from a shortened URL to the original URL.
3. **Caching**: Caches URL mappings in Redis for faster retrieval.
4. **Rate Limiting**: Limits the number of requests from a user within a specific time window.
5. **Expiration**: URLs are assigned an expiration date (default of 30 days), after which they are no longer accessible.
6. **Database**: Utilizes PostgreSQL or SQLite for storing URL mappings, with Redis as a cache layer.
7. **Error Handling**: Robust error handling with custom messages and appropriate HTTP status codes.

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
1. Ensure Docker and Docker Compose are installed and running.
2. Run the application using Docker Compose:
   ```bash
   docker compose up --build
   ```
3. The app will be accessible in development mode on http://localhost:8000, and for production, Nginx will expose the app on http://localhost:80 for external access.
## API Documentation

You can access the API documentation in the following ways:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Available APIs

### 1. Shorten URL
- **Endpoint**: `/urls/v1/shorten`
- **Method**: `POST`
- **Description**: Generates a short URL for a given original URL.
- **Sample Request**:
  ```json
  {
    "original_url": "https://example.com/some/long/path"
  }
  ```
- **Sample Response (201 Created)**:
  ```json
  {
    "short_url": "https://short.url/abc123",
    "expiration_date": "2024-12-31",
    "success": true,
    "reason": null,
    "original_url": "https://example.com/some/long/path"
  }
  ```
- **Possible Error Responses**:
  - **400 Bad Request**:
    ```json
    {
      "reason": "Invalid URL format",
      "details": "The provided URL is invalid.",
      "success": false
    }
    ```
    ```json
    {
      "detail": {
        "reason": "URL is too long",
        "details": "The provided URL is 24 characters long, but the maximum allowed length is 2048 characters.",
        "success": false
      }
    }
    ```

  - **429 Too Many Requests**:
    ```json
    {
      "detail": {
        "reason": "Rate limit exceeded",
        "details": "You have exceeded the limit of 10 requests per 60 seconds. Please wait before sending more requests.",
        "success": false
      }
    }
    ```

### 2. Redirect URL
- **Endpoint**: `/urls/v1/go/{short_url}`
- **Method**: `GET`
- **Description**: Redirects to the original URL based on the short URL.
- **Sample Request**:
  ```bash
  GET /urls/v1/go/abc123
  ```
- **Sample Response (302 Found)**:
  ```bash
  Location: https://example.com/some/long/path
  ```
- **Possible Error Responses**:
  - **404 Not Found**:
    ```json
    {
      "reason": "Short URL not found",
      "details": "The short URL pattern 'abc123' does not exist.",
      "success": false
    }
    ```
  - **410 Gone**:
    ```json
    {
      "reason": "Short URL expired",
      "details": "The short URL pattern 'abc123' has expired.",
      "success": false
    }
    ```
  - **429 Too Many Requests**:
    ```json
    {
      "detail": {
        "reason": "Rate limit exceeded",
        "details": "You have exceeded the limit of 10 requests per 60 seconds. Please wait before sending more requests.",
        "success": false
      }
    }
    ```