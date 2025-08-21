# main.py
import io
import logging
import zipfile
from typing import List, Optional

import fitz  # PyMuPDF
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from backend.redactor import redact_pdf_bytes

# ----------------- FastAPI App -----------------
app = FastAPI(title="PDF Redaction API (In-Memory)")

# Allow cross-origin requests (important if UI is separate)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Audit Logging -----------------
LOG_FILE = "audit.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Guardrail: reject very large PDFs
MAX_PAGES = 300


# ----------------- Helpers -----------------
def _parse_pages(page_range: str) -> List[int]:
    """Convert comma-separated page numbers into int list (0-based)."""
    if not page_range:
        return []
    return [int(p.strip()) for p in page_range.split(",") if p.strip().isdigit()]


def _validate_pdf_header(pdf_bytes: bytes) -> None:
    """Quick sanity check: PDF must start with '%PDF-'."""
    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Invalid PDF file (bad header)")


def _check_page_limit(pdf_bytes: bytes) -> int:
    """Open PDF and ensure page count <= MAX_PAGES."""
    try:
        d = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=400, detail="Corrupt or unsupported PDF")

    try:
        n = len(d)
        if n > MAX_PAGES:
            raise HTTPException(status_code=400, detail=f"PDF exceeds {MAX_PAGES} pages")
        return n
    finally:
        d.close()


def _log_success(client: str, filename: str, words: List[str],
                 pages: Optional[List[int]], remove_images: bool, mode: str):
    """Write audit log on success."""
    logging.info(
        f"SUCCESS [{mode}]: Client={client}, File={filename}, Words={words}, "
        f"Pages={pages if pages else 'ALL'}, RemoveImages={remove_images}"
    )


def _log_failure(client: str, filename: str, error: str, mode: str):
    """Write audit log on failure."""
    logging.error(f"FAILURE [{mode}]: Client={client}, File={filename}, Error={error}")


# ----------------- Single File Endpoint -----------------
@app.post("/redact/")
async def redact_pdf(
    request: Request,
    file: UploadFile = File(...),
    words: str = Form(""),
    page_range: str = Form(""),
    remove_images: str = Form("False"),
    placeholder: str = Form(""),
):
    """
    Redact a single PDF in-memory.
    Returns a downloadable PDF stream.
    """
    client_ip = request.client.host if request and request.client else "unknown"
    mode = "single"

    try:
        # Ensure valid file extension
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only .pdf files are allowed")

        # Read file fully into memory
        file_bytes = await file.read()

        # Quick validations
        _validate_pdf_header(file_bytes)
        total_pages = _check_page_limit(file_bytes)

        # Prepare redaction inputs
        words_to_redact = [w.strip() for w in words.split(",") if w.strip()]
        pages = _parse_pages(page_range)

        if pages and any(p < 0 or p >= total_pages for p in pages):
            raise HTTPException(status_code=400, detail="Page index out of range")

        # Perform redaction (in memory)
        redacted_bytes = redact_pdf_bytes(
            pdf_bytes=file_bytes,
            words_to_redact=words_to_redact,
            pages_0_based=pages if pages else None,
            remove_images=remove_images.lower() == "true",
            placeholder=placeholder.strip() or None,
        )

        # Log and return file as download
        _log_success(client_ip, file.filename, words_to_redact,
                     pages, remove_images.lower() == "true", mode)

        return StreamingResponse(
            io.BytesIO(redacted_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="redacted_{file.filename}"'},
        )

    except HTTPException as he:
        _log_failure(client_ip, file.filename, he.detail, mode)
        return JSONResponse(status_code=he.status_code, content={"error": he.detail})
    except Exception as e:
        _log_failure(client_ip, file.filename, str(e), mode)
        return JSONResponse(status_code=500, content={"error": str(e)})


# ----------------- Bulk Endpoint -----------------
@app.post("/redact_bulk/")
async def redact_bulk_pdfs(
    request: Request,
    files: List[UploadFile] = File(...),
    words: str = Form(""),
    page_range: str = Form(""),
    remove_images: str = Form("False"),
    placeholder: str = Form(""),
):
    """
    Redact multiple PDFs in one go.
    Returns a ZIP archive of redacted files.
    """
    client_ip = request.client.host if request and request.client else "unknown"
    mode = "bulk"

    try:
        words_to_redact = [w.strip() for w in words.split(",") if w.strip()]
        requested_pages = _parse_pages(page_range)

        # Create in-memory ZIP to hold results
        zip_buf = io.BytesIO()
        processed_count = 0

        with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
            for f in files:
                try:
                    # Skip non-PDFs early
                    if not f.filename.lower().endswith(".pdf"):
                        _log_failure(client_ip, f.filename, "Not a PDF", mode)
                        continue

                    # Load and validate
                    pdf_bytes = await f.read()
                    _validate_pdf_header(pdf_bytes)
                    total_pages = _check_page_limit(pdf_bytes)

                    # Check requested pages fit this doc
                    pages_for_doc = requested_pages[:] if requested_pages else []
                    if pages_for_doc and any(p < 0 or p >= total_pages for p in pages_for_doc):
                        _log_failure(client_ip, f.filename, "Page index out of range", mode)
                        continue

                    # Redact and add to ZIP
                    redacted_bytes = redact_pdf_bytes(
                        pdf_bytes=pdf_bytes,
                        words_to_redact=words_to_redact,
                        pages_0_based=pages_for_doc if pages_for_doc else None,
                        remove_images=remove_images.lower() == "true",
                        placeholder=placeholder.strip() or None,
                    )
                    zipf.writestr(f"redacted_{f.filename}", redacted_bytes)
                    processed_count += 1

                    _log_success(client_ip, f.filename, words_to_redact,
                                 pages_for_doc, remove_images.lower() == "true", mode)

                except HTTPException as he:
                    _log_failure(client_ip, f.filename, he.detail, mode)
                    continue
                except Exception as e:
                    _log_failure(client_ip, f.filename, str(e), mode)
                    continue

        if processed_count == 0:
            raise HTTPException(status_code=400, detail="No valid PDFs were processed")

        zip_buf.seek(0)
        return StreamingResponse(
            zip_buf,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="bulk_redacted.zip"'},
        )

    except HTTPException as he:
        _log_failure(client_ip, "BULK", he.detail, mode)
        return JSONResponse(status_code=he.status_code, content={"error": he.detail})
    except Exception as e:
        _log_failure(client_ip, "BULK", str(e), mode)
        return JSONResponse(status_code=500, content={"error": str(e)})
