import os
import uuid
import logging
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings
from db import get_db, Base, engine
import models, schemas
from ocr import run_ocr_on_file, SupportedEngine

# ------------------------------
# Create DB tables
# ------------------------------
Base.metadata.create_all(bind=engine)

# ------------------------------
# FastAPI app initialization
# ------------------------------
app = FastAPI(title="OCR Text Extraction API", version="1.0.0", debug=True)

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("uvicorn.error")

# Serve frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join("static", "index.html"))

@app.get("/health", response_model=schemas.Health)
def health_check():
    return {"status": "ok"}

# ------------------------------
# Upload and process files
# ------------------------------
@app.post("/upload", response_model=schemas.OCRJobResult)
async def upload_and_process(
    file: UploadFile = File(...),
    engine: SupportedEngine = Query(SupportedEngine.tesseract),
    db=Depends(get_db),
):
    try:
        logger.info(f" Received file: {file.filename}, type={file.content_type}")
        logger.info(f" Using engine: {engine}")

        if file.content_type not in {"application/pdf", "image/tiff", "image/tif", "image/x-tiff"}:
            raise HTTPException(status_code=415, detail="Unsupported file format. Only PDF or TIFF allowed.")

        # Save file temporarily
        temp_id = uuid.uuid4().hex
        ext = ".pdf" if file.filename.lower().endswith(".pdf") else ".tiff"
        temp_path = os.path.join(settings.UPLOAD_DIR, f"{temp_id}{ext}")
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        contents = await file.read()
        if len(contents) > settings.MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail="File too large.")

        with open(temp_path, "wb") as f:
            f.write(contents)

        # Run OCR
        try:
            total_rows, total_pages = run_ocr_on_file(temp_path, file.filename, engine, db)
            logger.info(f" OCR done. Pages={total_pages}, Rows={total_rows}")
        except Exception as ocr_err:
            logger.exception(" OCR processing failed")
            raise HTTPException(status_code=500, detail=f"OCR failed: {ocr_err}")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        return {
            "file_name": file.filename,
            "engine": engine.value,
            "pages": total_pages,
            "rows_inserted": total_rows,
            "message": "OCR completed and results stored."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(" Unexpected error in /upload")
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------
# List uploaded files
# ------------------------------
@app.get("/files", response_model=List[schemas.FileSummary])
def list_files(db=Depends(get_db)):
    q = db.query(models.OCRResult.file_name, models.OCRResult.page_number).all()
    results = {}
    for f, p in q:
        if f not in results:
            results[f] = {"pages": 0, "rows": 0}
        results[f]["pages"] = max(results[f]["pages"], p)
        results[f]["rows"] += 1
    return [
        schemas.FileSummary(file_name=f, pages=v["pages"], rows=v["rows"])
        for f, v in results.items()
    ]

# ------------------------------
# Paginated OCR results
# ------------------------------
@app.get("/results", response_model=schemas.PaginatedResults)
def get_results(
    file_name: str = Query(...),
    page_number: Optional[int] = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    base = db.query(models.OCRResult).filter(models.OCRResult.file_name == file_name)
    if page_number:
        base = base.filter(models.OCRResult.page_number == page_number)
    total = base.count()
    items = (
        base.order_by(models.OCRResult.page_number, models.OCRResult.line_number)
        .limit(limit)
        .offset(offset)
        .all()
    )
    return {"total": total, "items": items}
