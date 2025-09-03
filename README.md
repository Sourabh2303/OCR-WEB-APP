[README (2).md](https://github.com/user-attachments/files/22122478/README.2.md)
# 📄 OCR Web App

An **OCR (Optical Character Recognition) Web Application** built with **FastAPI**, **Tesseract**, and **PaddleOCR**.  
This app allows users to upload **PDF** or **TIFF** documents and extracts text using the selected OCR engine.  
Extracted results are stored in a database and can be browsed via API endpoints or the included frontend.

---

## 🚀 Features
- 📂 Upload PDF/TIFF files  
- 🔎 Extract text using **Tesseract** or **PaddleOCR**  
- 🗄️ Store OCR results in a database  
- 📊 Paginated API to fetch OCR results  
- 🌐 Frontend UI served via FastAPI  
- ✅ Health check endpoint  
- ⚙️ CORS enabled for frontend-backend communication  

---

## 🛠️ Tech Stack
- **Backend**: FastAPI  
- **OCR Engines**: Tesseract OCR, PaddleOCR  
- **Database**: SQLite (default, can be swapped with Postgres/MySQL)  
- **Frontend**: HTML + JS + Bootstrap (served via FastAPI)  

---

## 📦 Installation

```bash
# 1. Clone the repository
git clone https://github.com/Sourabh2303/OCR-WEB-APP.git
cd OCR-WEB-APP

# 2. Create virtual environment
python -m venv .venv
# Windows PowerShell
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
uvicorn main:app --reload
```

---

## 📂 Project Structure
```
OCR-WEB-APP/
│── main.py
│── ocr.py
│── models.py
│── schemas.py
│── db.py
│── config.py
│── static/
│── requirements.txt
│── README.md
```

---

## 🔗 API Endpoints

**Health Check**
```
GET /health
```

**Upload File**
```
POST /upload  
(file: PDF/TIFF, engine: tesseract | paddleocr)
```

**List Files**
```
GET /files
```

**Get OCR Results (Paginated)**
```
GET /results?file_name=<file>&page_number=1&limit=50&offset=0
```

---

## 🖼️ Frontend
The frontend is served at [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## ⚡ Future Improvements
- [ ] Add support for JPG/PNG images  
- [ ] Enhance UI with preview of extracted text  
- [ ] Dockerize the application  
- [ ] Authentication for user-specific files  

---

## 📜 License
This project is licensed under the **MIT License**. Feel free to use and modify for your own projects.

---

👨‍💻 Developed by *Sourabh Kumar*
