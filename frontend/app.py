# app.py
import streamlit as st
import requests
import base64
import io
import zipfile

# Read API base URL securely from Streamlit secrets
API_BASE = st.secrets.get("API_BASE")



# Helper: PDF Preview

def show_pdf(file_bytes, label="PDF Preview"):
    """
    Render a PDF securely from memory inside an iframe.
    - Converts PDF bytes → base64 → inline preview.
    - Avoids writing to disk.
    """
    base64_pdf = base64.b64encode(file_bytes).decode("utf-8")
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="400" type="application/pdf"></iframe>'
    st.markdown(f"#### {label}", unsafe_allow_html=True)
    st.markdown(pdf_display, unsafe_allow_html=True)



# Streamlit UI Setup

st.title("PDF Redaction Tool")
# Toggle mode: Single vs Bulk
mode = st.radio("Choose Mode", ["Single File", "Bulk Files"])



# SINGLE FILE MODE

if mode == "Single File":
    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
    words = st.text_input("Enter words to redact (comma-separated)")
    pages = st.text_input("Enter page numbers (Page number starts at 0 | comma-separated - 0,1,2 | field optional)")
    remove_images = st.checkbox("Remove images/logos")

    if uploaded_file is not None:
        # Keep original file in memory and preview
        original_bytes = uploaded_file.read()
        show_pdf(original_bytes, label="Original PDF")
        uploaded_file.seek(0)  # reset pointer so it can be re-read

    # Run redaction via API
    if st.button("Redact PDF") and uploaded_file:
        with st.spinner("Processing securely in memory..."):
            # Send PDF bytes to FastAPI service
            files = {"file": (uploaded_file.name, io.BytesIO(original_bytes), "application/pdf")}
            data = {"words": words, "page_range": pages, "remove_images": str(remove_images)}
            response = requests.post(f"{API_BASE}/redact/", files=files, data=data)

            if response.status_code == 200:
                redacted_bytes = response.content
                st.success("Redaction complete")

                # Preview + download redacted PDF
                show_pdf(redacted_bytes, label="Redacted PDF")
                st.download_button(
                    "Download Redacted PDF",
                    redacted_bytes,
                    file_name=f"redacted_{uploaded_file.name}"
                )
            else:
                st.error(f"Error: {response.json().get('error')}")


# BULK FILE MODE

else:
    uploaded_files = st.file_uploader("Upload multiple PDFs", type=["pdf"], accept_multiple_files=True)
    words = st.text_input("Enter words to redact (comma-separated)")
    pages = st.text_input("Enter page numbers (Page number starts at 0 | comma-separated - 0,1,2 | field optional)")
    remove_images = st.checkbox("Remove images/logos (bulk)")

    # Show Original Previews
    if uploaded_files:
        st.subheader("Original PDFs Preview")
        for f in uploaded_files:
            file_bytes = f.read()
            with st.expander(f"Original: {f.name}"):
                show_pdf(file_bytes, label=f"Original PDF: {f.name}")
            f.seek(0)

    # Run bulk redaction via API
    if st.button("Redact PDFs (Bulk)") and uploaded_files:
        with st.spinner("Processing multiple files securely in memory..."):
            # Prepare in-memory multipart upload
            files = [("files", (f.name, io.BytesIO(f.read()), "application/pdf")) for f in uploaded_files]
            data = {"words": words, "page_range": pages, "remove_images": str(remove_images)}
            response = requests.post(f"{API_BASE}/redact_bulk/", files=files, data=data)

            if response.status_code == 200:
                st.success("Bulk redaction complete")

                # Store redacted results in session_state
                if "redacted_pdfs" not in st.session_state:
                    st.session_state["redacted_pdfs"] = {}
                st.session_state["redacted_pdfs"].clear()

                zip_bytes = io.BytesIO(response.content)
                with zipfile.ZipFile(zip_bytes, "r") as zip_ref:
                    for filename in zip_ref.namelist():
                        st.session_state["redacted_pdfs"][filename] = zip_ref.read(filename)

                # Download all in a single ZIP
                st.download_button(
                    "Download All Redacted PDFs (ZIP)",
                    response.content,
                    file_name="redacted_bulk.zip"
                )
            else:
                st.error(f"Error: {response.json().get('error')}")

    # Show Redacted Previews
    if "redacted_pdfs" in st.session_state and st.session_state["redacted_pdfs"]:
        st.subheader("Redacted PDFs Preview")
        for filename, pdf_bytes in st.session_state["redacted_pdfs"].items():
            with st.expander(f"Redacted: {filename}"):
                show_pdf(pdf_bytes, label=f"Redacted PDF: {filename}")
                st.download_button(
                    f"Download {filename}",
                    pdf_bytes,
                    file_name=filename
                )
