
import sys
from sqlmodel import Session, select
from app.core.database import engine, init_db
from app.models.user import User
from app.models.document import Document

def seed_public():
    print("Running public database seeding... ")
    # Logic removed as per request to avoid file persistence issues
    pass

if __name__ == "__main__":
    try:
        seed_public()
    except Exception as e:
        print(f"Error during seeding: {e}")
        sys.exit(1)