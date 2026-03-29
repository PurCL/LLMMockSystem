import os
import sys
from sqlmodel import Session, select
from app.core.database import engine, init_db
from app.models.user import User
from app.models.document import Document

def seed_data():
    print("Running database seeding...")
    
    # Initialize DB (Create tables)
    init_db()
    
    setup_mode = os.getenv("SETUP_MODE", "public").lower()
    print(f"Setup Mode: {setup_mode}")

    with Session(engine) as session:
        if setup_mode == "private":
            print("Seeding PRIVATE data...")
            seed_private(session)
        else:
            print("Seeding PUBLIC data...")
            seed_public(session)
        
        session.commit()
    
    print("Seeding completed successfully.")

def seed_public(session: Session):
    # Check if demo user exists
    user = session.exec(select(User).where(User.nickname == "Demo User")).first()
    if not user:
        user = User(browser_id="demo-browser-id", nickname="Demo User")
        session.add(user)
        print("created 'Demo User'")
    else:
        print("'Demo User' already exists")

def seed_private(session: Session):
    # Check if test user exists
    user = session.exec(select(User).where(User.nickname == "Test User")).first()
    if not user:
        user = User(browser_id="test-browser-id", nickname="Test User")
        session.add(user)
        print("Created 'Test User'")
    else:
        print("'Test User' already exists")

if __name__ == "__main__":
    try:
        seed_data()
    except Exception as e:
        print(f"Error during seeding: {e}")
        sys.exit(1)
