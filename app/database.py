from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import DATABASE_URL

# Database configuration: check for SQLite and configure engine accordingly
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

Base = declarative_base()

# Set up the database engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency injection: Retrieve a new database session per request
def get_db():
    """
    Provides a new SQLAlchemy database session for each request.

    Yields:
        Session: A database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize the database
def init_db() -> None:
    """
    Initialize the database by creating all tables defined in the models.
    """
    Base.metadata.create_all(bind=engine)
