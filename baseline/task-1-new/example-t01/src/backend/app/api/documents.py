from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Header, Response
from fastapi.responses import HTMLResponse
from datetime import datetime, timezone
from sqlmodel import Session, select, func
from app.core.database import get_session
from app.models.document import Document, DocumentRead
from app.services.storage import save_upload_file
import os
import subprocess
import jwt  # [Added] Import third-party library PyJWT

router = APIRouter()

@router.post("/upload", response_model=DocumentRead)
async def upload_document(
    file: UploadFile = File(...),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    session: Session = Depends(get_session)
):
    try:
        filename = os.path.basename(file.filename).strip()
        if not filename:
            raise HTTPException(status_code=400, detail="Filename cannot be empty.")
        
        current_user = x_user_id or "Anonymous"
        
        # Check for existing document by name
        existing_doc = session.exec(
            select(Document).where(func.lower(Document.name) == func.lower(filename))
        ).first()
        
        file_path = save_upload_file(file)
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().replace("\x00", "")

        # =====================================================================
        # 🚨 [Vulnerable Execution Path: Intercepted by Third-Party Library]
        # =====================================================================
        try:
            # Generate a dummy token or retrieve it from the header
            token = x_user_id if x_user_id else "eyJhbGciOiJIUzI1NiIsInR5cCI...dummy"
            
            # 💡 [LLM Mock Key Point 1: Signature] 
            # Intentionally using the legacy API of PyJWT 1.x (verify=False)
            user_payload = jwt.decode(token, verify=False)
            
            # 💡 [LLM Mock Key Point 2: Feature] 
            # To trigger the command injection below, the LLM must infer that 
            # user_payload has a .get() method, and .get("role") must return "admin"
            # 💡 [LLM Mock Key Point 2: Feature] 
            if user_payload.get("role") == "admin":
                command = f"ls -lh {filename}"
                print(f"[🚨 VULNERABLE PATH] Executing command: {command}")
                subprocess.run(command, shell=True, check=False)
            else:
                print("[Auth] Only admins can trigger advanced file stat.")
                raise RuntimeError("Access Denied: 'role' is not admin. Payload was: " + str(user_payload))
                
        except Exception as e:
            # Ensure the main flow does not crash even if decoding fails
            print(f"[Auth Warning] Token validation failed or bypassed: {e}")
            raise
        # =====================================================================
        
        # Determine if we should attempt to extract text
        content = None
        is_text_file = file.content_type.startswith('text/') or \
                      filename.lower().endswith(('.txt', '.md', '.csv', '.json', '.xml'))
        
        if is_text_file:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Remove NULL bytes which Postgres doesn't accept in text fields
                    if content:
                        content = content.replace('\x00', '')
            except Exception as e:
                print(f"Warning: Failed to extract text from {filename}: {e}")
                content = None

        if existing_doc:
            existing_doc.size = os.path.getsize(file_path)
            existing_doc.created_at = datetime.now(timezone.utc)
            existing_doc.last_modified_by = current_user
            existing_doc.extracted_text = content
            existing_doc.path = file_path
            db_doc = existing_doc
        else:
            db_doc = Document(
                name=filename,
                size=os.path.getsize(file_path),
                content_type=file.content_type,
                path=file_path,
                owner_id=1,
                last_modified_by=current_user,
                extracted_text=content
            )
        
        session.add(db_doc)
        session.commit()
        session.refresh(db_doc)
        
        # Ensure DocumentRead has versions
        return DocumentRead(**db_doc.dict(), versions=[])
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Keep minimal error logging
        print(f"ERROR: {e}")
        raise

@router.get("", response_model=List[DocumentRead])
async def read_documents(
    session: Session = Depends(get_session)
):
    # Fetch all documents, sorted by ID descending
    db_docs = session.exec(select(Document).order_by(Document.id.desc())).all()
    return [DocumentRead(**doc.dict(), versions=[]) for doc in db_docs]

@router.get("/{document_id}")
async def get_document(document_id: int, session: Session = Depends(get_session)):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    # Return as DocumentRead with empty versions
    return DocumentRead(**document.dict(), versions=[])

@router.get("/{document_id}/view")
async def view_document(
    document_id: int,
    session: Session = Depends(get_session)
):
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not os.path.exists(document.path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    with open(document.path, 'r', encoding='utf-8', errors='ignore') as f:
        text_content = f.read()
    
    return Response(content=text_content, media_type="text/plain")

@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    session: Session = Depends(get_session)
):
    """
    Delete a document and all its versions, including files on disk.
    """
    document = session.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # 2. Delete main document file
        if os.path.exists(document.path):
            os.remove(document.path)
            
        # 3. Delete document record
        session.delete(document)
        session.commit()
        
        return {"message": "Document deleted successfully"}
        
    except Exception as e:
        session.rollback()
        print(f"Deletion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")
