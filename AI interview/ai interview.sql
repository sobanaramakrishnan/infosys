CREATE DATABASE ai_interview;
USE ai_interview;

CREATE TABLE interview_questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question TEXT NOT NULL
);

CREATE TABLE user_answers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_id INT,
    answer TEXT,
    FOREIGN KEY (question_id) REFERENCES interview_questions(id)
);
