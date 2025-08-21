import fitz  # PyMuPDF
import os

# Secure filename handling
def safe_filename(filename: str) -> str:
    return os.path.basename(filename)

# Core redaction logic
def redact_pdf(input_path: str, output_path: str, words_to_redact=None, page_range=None, remove_images=False, placeholder="[REDACTED]"):
    doc = fitz.open(input_path)
    words_to_redact = words_to_redact or []

    for page_num, page in enumerate(doc, start=1):
        # Apply only selected pages if provided
        if page_range and page_num not in page_range:
            continue

        # Redact words
        for word in words_to_redact:
            matches = page.search_for(word)
            for rect in matches:
                page.add_redact_annot(rect, text=placeholder, fill=(0, 0, 0))
        page.apply_redactions()

        # Optionally remove images/logos
        if remove_images:
            images = page.get_images(full=True)
            for img in images:
                xref = img[0]
                doc._deleteObject(xref)

    doc.save(output_path)
    doc.close()
