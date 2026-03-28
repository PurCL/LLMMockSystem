import os
import time
from sqlmodel import SQLModel, create_engine, Session
# Import models here to ensure they are registered with SQLModel.metadata
from app.models.user import User
from app.models.document import Document

# Database connection URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_engine(DATABASE_URL, echo=True)

def get_session():
    with Session(engine) as session:
        yield session

def init_db():
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            print(f"Attempting to connect to database (attempt {attempt + 1}/{max_retries})...")
            SQLModel.metadata.create_all(engine)
            print("Database tables created successfully!")
            return
        except Exception as e:
            print(f"Failed to connect to database: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print("Max retries reached. Database initialization failed.")
                raise

