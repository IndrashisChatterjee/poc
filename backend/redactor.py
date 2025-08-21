# redactor.py
from io import BytesIO
from typing import Iterable, List, Optional
import fitz  # PyMuPDF

def redact_pdf_bytes(
    pdf_bytes: bytes,
    words_to_redact: Optional[List[str]] = None,
    pages_0_based: Optional[Iterable[int]] = None,
    remove_images: bool = False,
    placeholder: Optional[str] = None,
) -> bytes:
    """
    Core PDF redaction logic (in-memory only).
    - Takes raw PDF bytes as input and returns new redacted PDF bytes.
    - Works fully in memory → avoids writing sensitive data to disk.
    """

    # Open PDF securely from memory
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        total_pages = len(doc)

        # Decide which pages to redact (default = all pages)
        if pages_0_based is None or len(list(pages_0_based)) == 0:
            target_pages = range(total_pages)
        else:
            # De-duplicate + filter only valid page numbers
            target_pages = sorted({p for p in pages_0_based if 0 <= p < total_pages})

        # Clean input word list (remove empty values)
        words = [w for w in (words_to_redact or []) if w]

        for pno in target_pages:
            page = doc[pno]

            # Redact text matches
            for w in words:
                for rect in page.search_for(w):
                    # Draw black box, optionally overlay placeholder text
                    if placeholder:
                        page.add_redact_annot(rect, text=placeholder, fill=(0, 0, 0))
                    else:
                        page.add_redact_annot(rect, fill=(0, 0, 0))

            # Redact images/logos if requested
            if remove_images:
                for img in page.get_images(full=True):
                    xref = img[0]
                    for rect in page.get_image_rects(xref):
                        page.add_redact_annot(rect, fill=(0, 0, 0))

            # Apply all redaction annotations for this page
            page.apply_redactions()

        # Save final document back to memory
        out_buf = BytesIO()
        doc.save(out_buf, garbage=4, deflate=True)  # garbage/deflate = cleanup + compress
        out_buf.seek(0)
        return out_buf.getvalue()

    finally:
        # Always release resources
        doc.close()
