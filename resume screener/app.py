from fastapi import FastAPI, Form, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sklearn.preprocessing import LabelEncoder
import pickle
import pandas as pd
from xgboost import XGBClassifier
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from io import StringIO
from dotenv import load_dotenv
import os
from fastapi import Request

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app and templates
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Load the pre-trained model
with open('resume_model.pkl', 'rb') as model_file:
    model = pickle.load(model_file)

# Load the LabelEncoder for the target column
with open('label_encoder.pkl', 'rb') as label_file:
    label_encoder = pickle.load(label_file)

# Function to send email
def send_email(to_email, subject, body):
    sender_email = os.getenv("EMAIL_USER")  # Load email user from .env
    sender_password = os.getenv("EMAIL_PASSWORD")  # Load email password from .env
    receiver_email = to_email

    # Create the email content
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Setup the SMTP server
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender_email, sender_password)

    # Send email
    server.sendmail(sender_email, receiver_email, msg.as_string())
    server.quit()

# Route to render the HTML form
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Route to handle the file upload and prediction
@app.post("/predict/")
async def predict_resume(file: UploadFile = File(...)):
    # Read the uploaded file
    content = await file.read()
    df = pd.read_csv(StringIO(content.decode("utf-8")))

    # Preprocessing the file for prediction
    target_column = 'Performance'  # Replace with your target column

    # Encode Categorical Features (except target column)
    categorical_features = df.select_dtypes(include=['object']).columns.tolist()
    categorical_features.remove(target_column)  # Remove target column from the list
    df[categorical_features] = df[categorical_features].apply(LabelEncoder().fit_transform)

    # Separate Features and Target
    feature_columns = [col for col in df.columns if col != target_column]
    X = df[feature_columns]

    # Make Predictions
    y_pred = model.predict(X)
    predicted_label = label_encoder.inverse_transform(y_pred)[0]  # Convert prediction back to original label

    # Log predicted label for debugging
    print(f"Predicted label: {predicted_label}")

    # Send Email to Candidate (replace with the correct email address)
    candidate_email = "aaronvsam289@gmail.com"  # Replace this with the recipient email

    if predicted_label == 'Select':
        send_email(candidate_email, "Interview Result: Selected", "Congratulations! You have been selected for the interview.")
        return {"prediction": "Selected", "message": "An email has been sent to the candidate."}
    else:
        send_email(candidate_email, "Interview Result: Rejected", "We regret to inform you that you have been rejected.")
        return {"prediction": "Rejected", "message": "An email has been sent to the candidate."}
