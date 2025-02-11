import fitz
import smtplib
from flask import Flask, render_template, request, jsonify
import mysql.connector
import google.generativeai as genai
from dotenv import load_dotenv
import os
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.utils import secure_filename

# Load environment variables and configure GenAI
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-pro")
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER  # Set the UPLOAD_FOLDER in the app config
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE")
)
cursor = db.cursor()
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = int(os.getenv("MAIL_PORT"))
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
HR_EMAIL = os.getenv("HR_EMAIL")

# Function to get a response from the Gemini model
def get_gemini_response(input_text, pdf_content, prompt):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        pdf_page_content = pdf_content[0] if pdf_content else ""
        response = model.generate_content([input_text, pdf_page_content, prompt])
        return response.text
    except Exception as e:
        return f"Error generating response: {str(e)}"

# Grammar checking using Gemini model
def check_grammar(text):
    grammar_prompt = """
    You are a grammar-checking assistant. Check the provided text for grammatical, spelling, or stylistic errors 
    and provide feedback with improvement suggestions.
    """
    return get_gemini_response(text, [], grammar_prompt)

PROMPTS = {
    "about": "Evaluate the provided resume against the job description. Highlight strengths and weaknesses.",
    "percentage": "Compare the resume to the job description and provide a percentage match, missing keywords, and final thoughts.",
    "suggestion": "Suggest improvements to the resume based on the job description.",
    "skills": "Identify essential skills in the job description and check if they are included in the resume.",
    "format": "Evaluate the resume's design and layout, and suggest improvements in structure and readability.",
    "breakdown": "Evaluate each section of the resume and provide match scores and improvement areas.",
    "density": "Analyze the frequency of important keywords from the job description in the resume.",
    "experience": "Compare the experience requirements in the job description with the resume.",
    "grammar": "Check the provided text for grammatical, spelling, or stylistic errors."
}

# Routes
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ats_checker")
def ats_checker():
    return render_template("ats_checker.html")

@app.route("/resume_screener")
def resume_screening():
    return render_template("resume_screener.html")

@app.route("/aivocate")
def aivocate():
    return render_template("aivocate.html")

@app.route('/process', methods=['POST'])
def process():
    try:
        input_text = request.form.get("jobDescription", "")
        action = request.form.get("action", "")
        uploaded_file = request.files.get("resumeFile")

        if not uploaded_file:
            return jsonify({"error": "Please upload a resume."})

        # Extract text from the PDF
        pdf_text = ""
        with fitz.open(stream=uploaded_file.read(), filetype="pdf") as pdf_document:
            for page in pdf_document:
                pdf_text += page.get_text("text")

        # Process the resume against the job description based on the action
        if action in PROMPTS:
            response = get_gemini_response(input_text, [pdf_text], PROMPTS[action])
            return jsonify({"response": response})
        else:
            return jsonify({"error": "Invalid action selected."})

    except Exception as e:
        return jsonify({"error": str(e)})

def extract_text_from_pdf(filepath):
    """Extracts text from a PDF file."""
    doc = fitz.open(filepath)
    text = ""
    for page in doc:
        text += page.get_text("text")  # Extracts text from each page
    return text

def process_resume(job_desc, resume_text):
    """Compares resume text with job description using Gemini AI and provides reasons."""
    model = genai.GenerativeModel("gemini-pro")
    prompt = f"""
    Compare the following resume with the job description and provide a match percentage.
    Also, explain why the candidate is a good or poor match.

    Job Description:
    {job_desc}

    Resume:
    {resume_text}

    Respond strictly in this format:
    Match Percentage: <percentage>
    Reason: <brief explanation>
    """

    response = model.generate_content(prompt)

    try:
        lines = response.text.strip().split("\n")
        match_percentage = float(lines[0].replace("Match Percentage:", "").strip().replace("%", ""))
    except Exception:
        match_percentage = 0.0

    return match_percentage

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        job_desc = request.form["job_desc"]
        resume = request.files["resume"]
        name = request.form["name"]  # Get candidate's name
        email = request.form["email"]

        if resume:
            filename = secure_filename(resume.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            resume.save(filepath)

            resume_text = extract_text_from_pdf(filepath)
            match_percentage = process_resume(job_desc, resume_text)

            send_email(name, email, match_percentage)  # Pass only name and match percentage to email function

            return jsonify({"match": match_percentage})

    return render_template("resume_screener.html")

def send_email(name, to_email, match_percentage):
    """Sends an email with the selection or rejection result."""
    greeting = f"Dear {name},\n\n"

    if match_percentage > 50:
        subject = "Resume Screening Result - Shortlisted"
        body = f"""
        {greeting}
        Congratulations! You have been shortlisted! 🎉
        """
    else:
        subject = "Resume Screening Result - Not Shortlisted"
        body = f"""
        {greeting}
        Thank you for applying. Unfortunately, you are not shortlisted at this time. ❌
        """

    msg = MIMEMultipart()
    msg["From"] = MAIL_USERNAME
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.sendmail(MAIL_USERNAME, to_email, msg.as_string())
    except Exception as e:
        print("Error sending email:", str(e))

@app.route("/start_interview", methods=["POST"])
def start_interview():
    job_description = request.form["job_description"]
    email = request.form["email"]
    resume = request.files["resume"]

    filename = secure_filename(resume.filename)
    resume_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    resume.save(resume_path)

    cursor.execute(
        "INSERT INTO interviews (job_description, resume_path, email) VALUES (%s, %s, %s)",
        (job_description, resume_path, email),
    )
    db.commit()
    interview_id = cursor.lastrowid

    # Generate first question
    prompt = f"Based on the job description: {job_description}, generate a technical interview question."
    response = model.generate_content(prompt)
    question = response.text

    cursor.execute("INSERT INTO interview_questions (interview_id, question) VALUES (%s, %s)", (interview_id, question))
    db.commit()

    return jsonify({"interview_id": interview_id, "question": question})

@app.route("/answer", methods=["POST"])
def answer():
    interview_id = request.json.get("interview_id")
    user_answer = request.json.get("answer")

    cursor.execute("SELECT question FROM interview_questions WHERE interview_id = %s", (interview_id,))
    questions = [row[0] for row in cursor.fetchall()]

    cursor.execute("SELECT answer FROM interview_answers WHERE interview_id = %s", (interview_id,))
    answers = [row[0] for row in cursor.fetchall()]

    # Store user's answer
    cursor.execute("INSERT INTO interview_answers (interview_id, answer) VALUES (%s, %s)", (interview_id, user_answer))
    db.commit()

    # Generate score and remarks
    prompt = f"Evaluate the answer: {user_answer} for the question: {questions[-1]}. Provide a score (out of 10) and a remark."
    response = model.generate_content(prompt)
    evaluation = response.text.split("\n")

    # Extract score and remarks safely
    score = 0
    remark = "No remark provided"
    for line in evaluation:
        score_match = re.search(r"(\d+)(?:/10|\s*out\s*of\s*10)?", line)
        if score_match:
            score = int(score_match.group(1))
        if "remark" in line.lower():
            remark = line.split(":")[-1].strip() or "No remark provided"

    cursor.execute("INSERT INTO interview_scores (interview_id, score, remark) VALUES (%s, %s, %s)", (interview_id, score, remark))
    db.commit()

    if len(answers) == 4:
        send_email_feedback(interview_id)
        return jsonify({"message": "Thank you! The interview is over. Check your email for results."})

    prev_questions = " ".join(questions)
    prev_answers = " ".join(answers + [user_answer])
    prompt = f"Given previous questions: {prev_questions} and answers: {prev_answers}, generate a follow-up question."
    response = model.generate_content(prompt)
    next_question = response.text

    cursor.execute("INSERT INTO interview_questions (interview_id, question) VALUES (%s, %s)", (interview_id, next_question))
    db.commit()

    return jsonify({"question": next_question})

def send_email_feedback(interview_id):
    # Fetch interview and candidate details
    cursor.execute("SELECT job_description, email FROM interviews WHERE id = %s", (interview_id,))
    interview_details = cursor.fetchone()
    job_description, email = interview_details

    # Extract candidate name from email
    candidate_name_match = re.match(r"([^@]+)", email)
    candidate_name = candidate_name_match.group(1).replace(".", " ").title() if candidate_name_match else "Candidate"

    # Fetch scores
    cursor.execute("SELECT score FROM interview_scores WHERE interview_id = %s", (interview_id,))
    scores = cursor.fetchall()

    # Calculate overall result and reasons
    total_score = sum(score[0] for score in scores)
    avg_score = total_score / len(scores) if scores else 0
    if avg_score >= 7:
        result = "Selected"
        overall_reason = (
            "The candidate demonstrated strong technical skills, effective communication, "
            "and a clear understanding of the job requirements, making them an ideal fit for the role."
        )
    else:
        result = "Rejected"
        overall_reason = (
            "The candidate did not meet the required expectations in key performance areas such as "
            "technical expertise, problem-solving, or communication skills. Further training or preparation may be needed."
        )

    # Create email content
    msg = MIMEMultipart()
    msg["From"] = MAIL_USERNAME
    msg["To"] = HR_EMAIL
    msg["Subject"] = f"Interview Feedback for {candidate_name}"
    email_body = (
        f"Dear HR Team,\n\n"
        f"The interview for the job description '{job_description}' has been completed.\n\n"
        f"Candidate Email: {email}\n"
        f"Result: {result}\n\n"
        f"Reason: {overall_reason}\n\n"
        f"Best regards,\nAIvocate System"
    )
    msg.attach(MIMEText(email_body, "plain"))

    # Send email to HR
    with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
        server.starttls()
        server.login(MAIL_USERNAME, MAIL_PASSWORD)
        server.sendmail(MAIL_USERNAME, HR_EMAIL, msg.as_string())

if __name__ == "__main__":
    app.run(debug=True)