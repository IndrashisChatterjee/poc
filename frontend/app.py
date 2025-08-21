import streamlit as st
import requests
import base64

API_BASE = "http://127.0.0.1:8002"

st.title("📑 PDF Redaction Tool")

uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])
words = st.text_input("Enter words to redact (comma-separated)")
pages = st.text_input("Enter page numbers (comma-separated, optional)")
remove_images = st.checkbox("Remove images/logos")

def show_pdf(file_bytes, label="PDF Preview"):
    base64_pdf = base64.b64encode(file_bytes).decode("utf-8")
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="400" type="application/pdf"></iframe>'
    st.markdown(f"#### {label}", unsafe_allow_html=True)
    st.markdown(pdf_display, unsafe_allow_html=True)

if uploaded_file is not None:
    # Preview Original before processing
    show_pdf(uploaded_file.read(), label="Original PDF")
    uploaded_file.seek(0)  # Reset pointer for re-use

if st.button("Redact PDF") and uploaded_file:
    with st.spinner("Processing..."):
        files = {"file": uploaded_file}
        data = {"words": words, "page_range": pages, "remove_images": str(remove_images)}
        response = requests.post(f"{API_BASE}/redact/", files=files, data=data)

        if response.status_code == 200:
            st.success("✅ Redaction complete")

            # Show redacted preview
            show_pdf(response.content, label="Redacted PDF")

            # Download button
            st.download_button("Download Redacted PDF", response.content, file_name=f"redacted_{uploaded_file.name}")
        else:
            st.error(f"Error: {response.json().get('error')}")
