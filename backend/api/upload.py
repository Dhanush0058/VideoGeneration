import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.services.document_service import DocumentProcessor

router = APIRouter()

# Size limit: 15MB
MAX_FILE_SIZE = 15 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".txt"}

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Receives an uploaded PDF or TXT document, validates size and type,
    and extracts clean text formatting.
    """
    filename = file.filename
    _, ext = os.path.splitext(filename.lower())
    
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format. Only PDF and TXT files are accepted."
        )

    # Validate file size
    try:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail="File is too large. Maximum allowed size is 15MB."
            )
            
        # Text extraction
        if ext == ".pdf":
            extracted_text = DocumentProcessor.extract_text_from_bytes(content)
        else:
            # Try decoding as UTF-8, fallback to Latin-1
            try:
                extracted_text = content.decode("utf-8")
            except UnicodeDecodeError:
                extracted_text = content.decode("latin-1")
                
            extracted_text = DocumentProcessor.clean_text(extracted_text)

        if not extracted_text.strip():
            raise HTTPException(
                status_code=400,
                detail="The uploaded document seems empty or has no readable text content."
            )

        return {
            "filename": filename,
            "status": "success",
            "extracted_text": extracted_text,
            "character_count": len(extracted_text)
        }
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during text extraction: {str(e)}"
        )
