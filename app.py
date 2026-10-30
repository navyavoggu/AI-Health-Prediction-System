import os
from dotenv import load_dotenv
from google import genai
from flask import Flask, request, redirect, render_template_string
import sqlite3
import re
import math
import time
from datetime import datetime, date

app = Flask(__name__)
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None



def generate_health_remarks(glucose, haemoglobin, cholesterol):
    if client is None:
        raise RuntimeError("Gemini API key is missing. Check your .env file.")

    prompt = f"""
    Explain these health measurements in simple language:
    Glucose: {glucose}
    Haemoglobin: {haemoglobin}
    Cholesterol: {cholesterol}

    Give a short general informational explanation.
    Use plain text without Markdown symbols.
    Do not diagnose any disease.
    Explain that interpretation depends on units and clinical context.
    Recommend consulting a healthcare professional.
    """

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=prompt
            )

            if not response.text:
                raise RuntimeError("Gemini returned an empty response.")

            return response.text.strip()

        except Exception as e:
            error_message = str(e).upper()

            if ("503" in error_message or
                "UNAVAILABLE" in error_message or
                "429" in error_message or
                "RESOURCE_EXHAUSTED" in error_message):

                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue

            raise RuntimeError(f"Gemini AI failed: {e}")

    raise RuntimeError("Gemini is temporarily unavailable. Please try again.")


DATABASE = "patients.db"


# 1. Create the database and table
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                dob TEXT NOT NULL,
                email TEXT NOT NULL,
                glucose REAL NOT NULL,
                haemoglobin REAL NOT NULL,
                cholesterol REAL NOT NULL,
                remarks TEXT DEFAULT 'Pending AI integration'
            )
        """)


# 2. Validate patient details
def validate_patient(data):
    errors = []

    name = data.get("full_name", "").strip()
    email = data.get("email", "").strip()
    dob_text = data.get("dob", "").strip()

    if not name:
        errors.append("Full name is required.")

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        errors.append("Please enter a valid email address.")

    parsed_dob = None

    for fmt in ("%d/%m/%Y", "%d.%m.%Y"):
        try:
            parsed_dob = datetime.strptime(
                dob_text, fmt
            ).date()
            break
        except ValueError:
            continue

    if parsed_dob is None:
        errors.append("Enter a valid date using dd/mm/yyyy or dd.mm.yyyy.")
    elif parsed_dob > date.today():
        errors.append("Date of birth cannot be in the future.")

    values = {}

    for field in ("glucose", "haemoglobin", "cholesterol"):
        try:
            value = float(data.get(field, ""))
            if not math.isfinite(value) or value < 0:
                raise ValueError
            values[field] = value
        except (ValueError, TypeError):
            errors.append(f"{field.capitalize()} must be a valid non-negative number.")

    return errors, parsed_dob, values


# 3. HTML page
PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AI Health Prediction System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
          rel="stylesheet">
          <style>
              .table {
                  width: 100%;
                  table-layout: auto;
                }

                .remarks-cell {
                    min-width: 350px;
                    max-width: 500px;
                    white-space: normal;
                    overflow-wrap: anywhere;
                    line-height: 1.6;
                }

                .table-responsive {
                    overflow-x: auto;
                }
            </style>
</head>
<body class="bg-light">
<div class="container py-4">
    <h1 class="text-primary mb-2">AI Health Prediction System</h1>
    <p class="text-muted">Patient registration and record management</p>

    {% if errors %}
    <div class="alert alert-danger">
        <strong>Please correct these errors:</strong>
        <ul class="mb-0">
        {% for error in errors %}
            <li>{{ error }}</li>
        {% endfor %}
        </ul>
    </div>
    {% endif %}

    {% if success %}
    <div class="alert alert-success">{{ success }}</div>
    {% endif %}

    <div class="card shadow-sm mb-4">
        <div class="card-header fw-bold">Add Patient</div>
        <div class="card-body">
            <form method="POST" action="/add">
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label">Full Name</label>
                        <input class="form-control" name="full_name"
                               value="{{ form.get('full_name', '') }}" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Date of Birth</label>
                        <input class="form-control" name="dob"
                               placeholder="dd/mm/yyyy" value="{{ form.get('dob', '') }}"
                               required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Email Address</label>
                        <input class="form-control" name="email" type="text"
                               value="{{ form.get('email', '') }}" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Glucose</label>
                        <input class="form-control" name="glucose" type="number"
                               step="any" value="{{ form.get('glucose', '') }}" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Haemoglobin</label>
                        <input class="form-control" name="haemoglobin" type="number"
                               step="any" value="{{ form.get('haemoglobin', '') }}" required>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Cholesterol</label>
                        <input class="form-control" name="cholesterol" type="number"
                               step="any" value="{{ form.get('cholesterol', '') }}" required>
                    </div>
                </div>
                <button class="btn btn-primary mt-3" type="submit">
                    Add Patient
                </button>
            </form>
        </div>
    </div>

    <h2 class="h4 mb-3">Patient Records ({{ patients|length }})</h2>
    <div class="table-responsive bg-white">
        <table class="table table-bordered table-striped align-middle">
            <thead class="table-dark">
                <tr>
                    <th>ID</th><th>Name</th><th>DOB</th><th>Email</th>
                    <th>Glucose</th><th>Haemoglobin</th><th>Cholesterol</th>
                    <th>Remarks</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
            {% for p in patients %}
                <tr>
                    <td>{{ p[0] }}</td><td>{{ p[1] }}</td>
                    <td>{{ p[2] }}</td><td>{{ p[3] }}</td>
                    <td>{{ p[4] }}</td><td>{{ p[5] }}</td>
                    <td>{{ p[6] }}</td><td class="remarks-cell">{{ p[7] }}</td>
                    <td>
                        <a href="/edit/{{ p[0] }}"
                           class="btn btn-warning btn-sm">Edit</a>

                        <form method="POST"
                              action="/delete/{{ p[0] }}"
                              style="display:inline">
                           <button type="submit"
                                   class="btn btn-danger btn-sm">
                                Delete
                           </button>
                        </form>
                    </td>
                </tr>
            {% else %}
                <tr><td colspan="8" class="text-center text-muted">
                    No patient records yet.
                </td></tr>
            {% endfor %}
            </tbody>
        </table>
    </div>
    <p class="text-muted small">
        AI remarks will be enabled in the API integration stage.
        This application does not provide medical diagnoses.
    </p>
</div>
</body>
</html>
"""


# 4. Display patient form and records
@app.route("/")
def home():
    with sqlite3.connect(DATABASE) as conn:
        patients = conn.execute(
            "SELECT * FROM patients ORDER BY id"
        ).fetchall()

    return render_template_string(
        PAGE, patients=patients, errors=[],
        success=request.args.get("success"), form={}
    )


# 5. Validate and save a patient

@app.route("/add", methods=["POST"])
def add_patient():
    data = request.form
    errors, dob, values = validate_patient(data)

    if errors:
        with sqlite3.connect(DATABASE) as conn:
            patients = conn.execute(
                "SELECT * FROM patients ORDER BY id"
            ).fetchall()

        return render_template_string(
            PAGE,
            patients=patients,
            errors=errors,
            success=None,
            form=data
        ), 400

    # Check for an existing duplicate patient
    with sqlite3.connect(DATABASE) as conn:
        duplicate = conn.execute("""
            SELECT id FROM patients
            WHERE LOWER(TRIM(full_name)) = LOWER(TRIM(?))
            AND dob = ?
            AND LOWER(TRIM(email)) = LOWER(TRIM(?))
        """, (
            data["full_name"],
            dob.isoformat(),
            data["email"]
        )).fetchone()

        if duplicate:
            patients = conn.execute(
                "SELECT * FROM patients ORDER BY id"
            ).fetchall()

            return render_template_string(
                PAGE,
                patients=patients,
                errors=["This patient record already exists."],
                success=None,
                form=data
            ), 400

    # Generate AI remarks
    try:
        remarks = generate_health_remarks(
            values["glucose"],
            values["haemoglobin"],
            values["cholesterol"]
        )
    except Exception as e:
        return f"Gemini AI error: {e}", 502

    # Save patient
    with sqlite3.connect(DATABASE) as conn:
        conn.execute("""
            INSERT INTO patients
            (full_name, dob, email, glucose, haemoglobin,
             cholesterol, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data["full_name"].strip(),
            dob.isoformat(),
            data["email"].strip(),
            values["glucose"],
            values["haemoglobin"],
            values["cholesterol"],
            remarks
        ))

    return redirect("/?success=Patient+added+successfully")



# 6. Edit an existing patient
@app.route("/edit/<int:patient_id>", methods=["GET", "POST"])
def edit_patient(patient_id):
    with sqlite3.connect(DATABASE) as conn:
        patient = conn.execute(
            "SELECT * FROM patients WHERE id = ?",
            (patient_id,)
        ).fetchone()

        if patient is None:
            return "Patient not found", 404

        if request.method == "POST":
            data = request.form
            errors, dob, values = validate_patient(data)

            if errors:
                return (
                    "<h3>Validation errors</h3><ul>"
                    + "".join(f"<li>{e}</li>" for e in errors)
                    + "</ul><a href='/'>Back</a>"
                ), 400

            conn.execute("""
                UPDATE patients
                SET full_name = ?, dob = ?, email = ?,
                    glucose = ?, haemoglobin = ?, cholesterol = ?
                WHERE id = ?
            """, (
                data["full_name"].strip(),
                dob.isoformat(),
                data["email"].strip(),
                values["glucose"],
                values["haemoglobin"],
                values["cholesterol"],
                patient_id
            ))

            return redirect("/?success=Patient+updated+successfully")

    edit_page = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Edit Patient</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
              rel="stylesheet">
    </head>
    <body class="container py-4">
        <h2>Edit Patient</h2>
        <form method="POST">
            <label class="form-label">Full Name</label>
            <input class="form-control mb-3" name="full_name"
                   value="{{ p[1] }}" required>

            <label class="form-label">Date of Birth</label>
            <input class="form-control mb-3" name="dob"
                   value="{{ p[2][8:10] }}.{{ p[2][5:7] }}.{{ p[2][0:4] }}"
                   required>

            <label class="form-label">Email</label>
            <input class="form-control mb-3" name="email"
                   value="{{ p[3] }}" required>

            <label class="form-label">Glucose</label>
            <input class="form-control mb-3" name="glucose"
                   type="number" step="any" value="{{ p[4] }}" required>

            <label class="form-label">Haemoglobin</label>
            <input class="form-control mb-3" name="haemoglobin"
                   type="number" step="any" value="{{ p[5] }}" required>

            <label class="form-label">Cholesterol</label>
            <input class="form-control mb-3" name="cholesterol"
                   type="number" step="any" value="{{ p[6] }}" required>

            <button class="btn btn-primary" type="submit">Save Changes</button>
            <a class="btn btn-secondary" href="/">Cancel</a>
        </form>
    </body>
    </html>
    """

    return render_template_string(edit_page, p=patient)


# 7. Delete a patient
@app.route("/delete/<int:patient_id>", methods=["POST"])
def delete_patient(patient_id):
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.execute(
            "DELETE FROM patients WHERE id = ?",
            (patient_id,)
        )

        if cursor.rowcount == 0:
            return "Patient not found", 404

    return redirect("/?success=Patient+deleted+successfully")



# 8. Start the application
init_db()

if __name__ == "__main__":
    app.run(debug=True)
