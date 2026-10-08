import json
import os
import docx
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session
import PyPDF2
from ai import analyze_resume 
from db import Base, engine, SessionLocal

import models

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "secret123")

Base.metadata.create_all(bind=engine)


# home route

@app.route("/")
def home():
    return render_template("home.html")


# SIGNUP route

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template(
                "signup.html",
                error="Email and password are required."
            )

        db = SessionLocal()

        try:

            existing_user = (
                db.query(models.User)
                .filter_by(email=email)
                .first()
            )

            if existing_user:
                return render_template(
                    "signup.html",
                    error="User already exists."
                )

            user = models.User(
                email=email,
                password=password
            )
            

            db.add(user)
            db.commit()

            # Signup successful → Login page
            return redirect("/login")

        except Exception as e:

            db.rollback()

            return render_template(
                "signup.html",
                error=f"Signup error: {str(e)}"
            )

        finally:
            db.close()

    # Direct /signup URL → Signup page
    return render_template("signup.html") 

# LOGIN route


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        db = SessionLocal()

        try:

            user = (
                db.query(models.User)
                .filter_by(email=email)
                .first()
            )

            if user and user.password == password:

                # User login session
                session["user"] = user.email

                # Login successful → Dashboard
                return redirect("/dashboard")

            else:

                return render_template(
                    "login.html",
                    error="Invalid email or password."
                )

        finally:
            db.close()

    # Direct /login URL → Login page
    return render_template("login.html")



@app.route("/dashboard", methods=["POST", "GET"])
def dashboard():
    if "user" not in session:
        return redirect("/login")

    result = None

    if request.method == "POST":

        user_goal = request.form.get("role", "").strip()
        resume_text = request.form.get("resume", "").strip()

        # Get uploaded file
        file = request.files.get("file")

        
        if file and file.filename:

            filename = file.filename.lower()

            # PDF fill
            if filename.endswith(".pdf"):
                try:
                    pdf_reader = PyPDF2.PdfReader(file)

                    text = ""

                    for page in pdf_reader.pages:
                        text += page.extract_text() or ""

                    resume_text = text.strip()

                except Exception as e:
                    result = {
                        "error": f"PDF ERROR: {str(e)}"
                    }

            # DOCX fill
            elif filename.endswith(".docx"):
                try:
                    doc = docx.Document(file)

                    text = ""

                    for para in doc.paragraphs:
                        text += para.text + "\n"

                    resume_text = text.strip()

                except Exception as e:
                    result = {
                        "error": f"DOCX ERROR: {str(e)}"
                    }

            # TXT fill
            elif filename.endswith(".txt"):
                try:
                    resume_text = file.read().decode(
                        "utf-8"
                    ).strip()

                except Exception as e:
                    result = {
                        "error": f"TXT ERROR: {str(e)}"
                    }

            else:
                result = {
                    "error": "Only PDF, DOCX and TXT files are supported."
                }

        
        # CHECK INPUT
        if not resume_text:
            result = {
                "error": "Please paste your resume or upload a resume file."
            }

        elif not user_goal:
            result = {
                "error": "Please enter your target role."
            }


        # AI ANALYSIS
        if resume_text and user_goal and not result:
            try:
                result = analyze_resume(
                    resume_text,
                    user_goal
                )
                print("AI RESULT:", result)

                # SAVE REPORT
                db = SessionLocal()
                try:

                    user = (
                        db.query(models.User)
                        .filter_by(
                            email=session["user"]
                        )
                        .first()
                    )

                    if user:

                        report = models.Reports(
                            user_id=user.id,
                            resume_text=resume_text,
                            result=json.dumps(result)
                        )

                        db.add(report)
                        db.commit()

                finally:
                    db.close()

            except Exception as e:

                result = {
                    "error": f"AI ERROR: {str(e)}"
                }

    return render_template(
        "dashboard.html",
        user=session["user"],
        result=result
    )


# history
@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/login")

    db = SessionLocal()
    parsed_reports = []
    try:
        user = db.query(models.User).filter_by(email=session["user"]).first()
        if user:
            reports = db.query(models.Reports).filter_by(user_id=user.id).all()
            for r in reports:
                try:
                    parsed_result = json.loads(r.result)
                except Exception:
                    parsed_result = {}

                parsed_reports.append(
                    {"resume": r.resume_text, "result": parsed_result}
                )
    finally:
        db.close()

    return render_template("history.html", reports=parsed_reports)




@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")



if __name__ == "__main__":
    app.run(
        debug=True,
        use_reloader=False
    )