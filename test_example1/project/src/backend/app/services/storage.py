import shutil
import os
from pathlib import Path
from fastapi import UploadFile

# Determine the backend root directory (where uploads should live)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"

def init_storage():
    """Ensure upload directory exists."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def save_upload_file(upload_file: UploadFile, content: bytes = None) -> str:
    """
    Saves the uploaded file to the local filesystem (simulating Docker volume).
    Returns the file path.
    """
    try:
        init_storage()
        # Create a unique filename if needed, or stick to original for this phase
        # For simplicity in Phase 1, using original filename. 
        # In prod, we'd use UUIDs to prevent collision.
        file_path = UPLOAD_DIR / upload_file.filename
        
        with open(file_path, "wb") as buffer:
            if content:
                buffer.write(content)
            else:
                shutil.copyfileobj(upload_file.file, buffer)
            
        return str(file_path)
    finally:
        upload_file.file.close()
