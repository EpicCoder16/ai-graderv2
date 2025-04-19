from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import shutil
import docx
import pdfplumber
import os
from sentence_transformers import SentenceTransformer, util
from pydantic import BaseModel
import bcrypt
import db
from fastapi.responses import FileResponse
import logging

app = FastAPI()

# Mount the frontend directory at /static
# app.mount("/static", StaticFiles(directory="../frontend", html=True), name="frontend")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://epiccoder16.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the Sentence-BERT model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Global variable to store the answer key text
answer_key_text = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------ Helper Functions ------------------

def extract_text_from_docx(file_path: str):
    doc = docx.Document(file_path)
    return '\n'.join([para.text for para in doc.paragraphs])

def extract_text_from_pdf(file_path: str):
    with pdfplumber.open(file_path) as pdf:
        return ''.join([page.extract_text() for page in pdf.pages if page.extract_text()])

def compare_with_answer_key(extracted_text: str, answer_key: str):
    extracted_embedding = model.encode(extracted_text, convert_to_tensor=True)
    answer_key_embedding = model.encode(answer_key, convert_to_tensor=True)
    cosine_similarity = util.pytorch_cos_sim(extracted_embedding, answer_key_embedding)
    similarity_score = cosine_similarity.item()
    return {"similarity_score": similarity_score, "message": "Comparison complete."}

# ------------------ Routes ------------------

@app.get("/")
async def read_root():
    return FileResponse("../frontend/index.html")

@app.post("/api/upload_answer_key/")
async def upload_answer_key(file: UploadFile = File(...)):
    global answer_key_text
    file_location = f"uploads/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if file.filename.endswith('.docx'):
        answer_key_text = extract_text_from_docx(file_location)
    elif file.filename.endswith('.pdf'):
        answer_key_text = extract_text_from_pdf(file_location)
    else:
        return {"error": "Unsupported file type. Please upload a .docx or .pdf file."}

    return {"filename": file.filename, "message": "Answer key uploaded successfully!"}

@app.post("/api/upload/")
async def upload_file(file: UploadFile = File(...), user_id: int = Form(...)):
    try:
        logger.info(f"Attempting to upload file: {file.filename} for user: {user_id}")
        if not answer_key_text:
            logger.warning("Upload failed: Answer key not uploaded yet")
            return {
                "error": "Answer key is not uploaded yet.",
                "filename": file.filename,
                "comparison_result": None
            }

        # Create uploads directory if it doesn't exist
        os.makedirs("uploads", exist_ok=True)

        file_location = f"uploads/{file.filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if file.filename.endswith('.docx'):
            extracted_text = extract_text_from_docx(file_location)
        elif file.filename.endswith('.pdf'):
            extracted_text = extract_text_from_pdf(file_location)
        else:
            logger.warning(f"Upload failed: Unsupported file type for {file.filename}")
            return {
                "error": "Unsupported file type.",
                "filename": file.filename,
                "comparison_result": None
            }

        comparison_result = compare_with_answer_key(extracted_text, answer_key_text)
        similarity_score = comparison_result["similarity_score"]

        connection = db.get_connection()
        cursor = connection.cursor()
        try:
            logger.info(f"Storing comparison result in database for file: {file.filename}")
            cursor.execute("INSERT INTO comparisons (user_id, filename, similarity_score) VALUES (%s, %s, %s)",
                       (user_id, file.filename, similarity_score))
            connection.commit()
            logger.info("Comparison result stored successfully")
        except Exception as db_error:
            connection.rollback()
            logger.error(f"Database error during upload: {str(db_error)}")
            return {
                "error": "Database error occurred",
                "filename": file.filename,
                "comparison_result": None
            }
        finally:
            cursor.close()
            connection.close()

        return {
            "filename": file.filename,
            "extracted_text": extracted_text,
            "comparison_result": comparison_result
        }
    except Exception as e:
        logger.error(f"Error in upload_file: {str(e)}")
        return {
            "error": str(e),
            "filename": file.filename,
            "comparison_result": None
        }

@app.get("/api/comparisons/{user_id}")
def get_user_comparisons(user_id: int):
    connection = db.get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM comparisons WHERE user_id = %s ORDER BY timestamp DESC", (user_id,))
    results = cursor.fetchall()
    cursor.close()
    connection.close()
    return results

# ------------------ User Auth ------------------

class User(BaseModel):
    username: str
    password: str

@app.post("/api/register")
def register(user: User):
    connection = db.get_connection()
    cursor = connection.cursor()

    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())

    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                       (user.username, hashed_password))
        connection.commit()
    except Exception:
        raise HTTPException(status_code=400, detail="Username already exists")
    finally:
        cursor.close()
        connection.close()

    return {"message": "User registered successfully"}

@app.post("/api/login")
def login(user: User):
    try:
        logger.info(f"Attempting login for user: {user.username}")
        connection = db.get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM users WHERE username = %s", (user.username,))
            db_user = cursor.fetchone()
            
            if not db_user:
                logger.warning(f"Login failed: User {user.username} not found")
                raise HTTPException(status_code=401, detail="Invalid username or password")
                
            if not bcrypt.checkpw(user.password.encode('utf-8'), db_user["password_hash"].encode('utf-8')):
                logger.warning(f"Login failed: Invalid password for user {user.username}")
                raise HTTPException(status_code=401, detail="Invalid username or password")

            logger.info(f"Login successful for user: {user.username}")
            return {"message": "Login successful", "user_id": db_user["id"]}
        except Exception as e:
            logger.error(f"Database error during login: {str(e)}")
            raise HTTPException(status_code=500, detail="Database error occurred")
        finally:
            cursor.close()
            connection.close()
    except Exception as e:
        logger.error(f"Connection error during login: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not connect to database")
