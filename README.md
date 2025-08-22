
# PDF Redaction Tool  

A simple web app to securely redact sensitive text and images from PDFs. Works on single files or in bulk.  

---

##  Features  
- Upload one or many PDFs.  
- Redact specific words/phrases.  
- Choose page ranges if needed.  
- Optionally remove images/logos.  
- Preview original & redacted PDFs.  
- Download single files or ZIP for bulk.  
- All processing happens securely in memory.  

---

## Quick Start Guide

### 1. Clone Repository  
```bash
git clone https://github.com/IndrashisChatterjee/poc.git
cd poc
```

### 2. Create Virtual Environment  
```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### 3. Install Dependencies  
```bash
pip install -r requirements.txt
```

### 4. Configure Secrets  
Create a file at `.streamlit/secrets.toml` and set your API:  
```toml
API_BASE = "http://127.0.0.1:8002"
```

### 5. Run the App  
Backend:  
```bash
uvicorn backend.main:app --reload --port 8002
```  
Frontend:  
```bash
streamlit run frontend/app.py
```

---

## Project Folder Structure  
```
poc/
│
├── .streamlit/              
│   │── secrets.toml        
│
├── backend/                     
│   ├── main.py             
│   ├── redactor.py         
│   
├── frontend/
│   ├── app.py
│   
├── requirements.txt
├── venv
 
---
