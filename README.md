# Resume Screener - FastAPI Application

This is a simple resume screener application built with FastAPI. The application uses a pre-trained machine learning model to predict the performance (selected or rejected) of candidates based on their resume data, which is uploaded as a CSV file.

### Features

- **File Upload**: Upload a CSV file containing candidate data.
- **Prediction**: The model predicts whether the candidate is selected or rejected based on the provided data.
- **Email Notification**: An email is sent to the candidate with the result of the prediction (Selected/Rejected).
- **Frontend**: Simple HTML form to upload the resume.

### Technologies Used

- **Backend**: FastAPI
- **Machine Learning**: XGBoost
- **Email**: SMTP (Gmail)
- **Frontend**: HTML/CSS
- **Environment Variables**: dotenv for email credentials

### Requirements

- Python 3.7 or later
- Install the required libraries using pip:
  ```bash
  pip install -r requirements.txt


