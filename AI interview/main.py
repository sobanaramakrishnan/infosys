from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import mysql.connector
import google.generativeai as genai
from dotenv import load_dotenv
import os
import speech_recognition as sr

# Load environment variables
load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# MySQL Connection
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE")
    )

# Configure Google Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Home Page
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Generate interview questions using Gemini
@app.post("/generate_questions/")
async def generate_questions(job_description: str = Form(...)):
    prompt = f"Generate 5 interview questions for the following job description:\n{job_description}"
    
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    
    questions = response.text.split("\n")
    
    # Store questions in MySQL
    conn = get_db_connection()
    cursor = conn.cursor()
    for q in questions:
        cursor.execute("INSERT INTO interview_questions (question) VALUES (%s)", (q,))
    conn.commit()
    cursor.close()
    conn.close()

    return {"questions": questions}

# Convert voice to text
def speech_to_text(audio_file):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio = recognizer.record(source)
    return recognizer.recognize_google(audio)

# Save user response and get AI feedback
@app.post("/submit_answer/")
async def submit_answer(question_id: int = Form(...), answer: str = Form(None), voice: UploadFile = File(None)):
    if voice:
        with open("temp_audio.wav", "wb") as audio_file:
            audio_file.write(await voice.read())
        answer = speech_to_text("temp_audio.wav")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_answers (question_id, answer) VALUES (%s, %s)", (question_id, answer))
    conn.commit()
    
    # AI Feedback
    feedback_prompt = f"Evaluate this interview answer:\nQuestion ID: {question_id}\nAnswer: {answer}\nGive constructive feedback."
    model = genai.GenerativeModel("gemini-pro")
    feedback_response = model.generate_content(feedback_prompt)
    
    cursor.close()
    conn.close()
    
    return JSONResponse(content={"message": "Answer saved!", "feedback": feedback_response.text})
