AI Health Prediction System

Project Overview

A web-based application built using Python and Flask to manage patient health records and generate AI-powered informational remarks using Google Gemini.

Features

Add and view patient records.

Edit and delete patient records.

SQLite database integration.

Email and date-of-birth validation.

Duplicate patient detection.

AI-generated health remarks using Gemini API.

Responsive interface using Bootstrap 5.

Technologies Used

Python

Flask

SQLite

Google Gemini API

HTML and CSS

Bootstrap 5

Installation and Setup

Clone the repository:
git clone https://github.com/navyavoggu/AI-Health-Prediction-System.git

Open the project folder.

Create and activate a Python virtual environment.

Install dependencies:
pip install flask requests python-dotenv google-genai

Create a .env file and add your Gemini API key:
GEMINI_API_KEY=your_api_key_here

Run the application:
python app.py

Open your browser at:
http://127.0.0.1:5000/

Security

Never upload your .env file, API key, virtual environment, or patient database to GitHub.

Disclaimer

AI-generated remarks are for general informational purposes only and are not a medical diagnosis.
