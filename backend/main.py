from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
import os
from .redactor import redact_pdf, safe_filename

UPLOAD_DIR = "storage/uploads"
OUTPUT_DIR = "storage/outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI(title="PDF Redaction API")

@app.post("/redact/")
async def redact_pdf_api(
    file: UploadFile = File(...),
    words: str = Form(""),
    page_range: str = Form(""),
    remove_images: bool = Form(False)
):
    try:
        filename = safe_filename(file.filename)
        input_path = os.path.join(UPLOAD_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, f"redacted_{filename}")

        # Save uploaded file
        with open(input_path, "wb") as f:
            f.write(await file.read())

        # Parse inputs
        words_to_redact = [w.strip() for w in words.split(",") if w.strip()]
        pages = [int(p) for p in page_range.split(",") if p.strip().isdigit()] if page_range else None

        # Run redaction
        redact_pdf(input_path, output_path, words_to_redact, pages, remove_images)

        return FileResponse(output_path, filename=f"redacted_{filename}")
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
