from flask import Flask, render_template, request, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)


# MySQL connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="placement_db"
    )


# Home page
@app.route("/")
def home():
    return render_template("index.html")


# Login page
@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, name, password_hash FROM students WHERE email=%s",
            (email,)
        )
        student = cursor.fetchone()

        if (
            not student
            or not student["password_hash"]
            or not check_password_hash(student["password_hash"], password)
        ):
            return "Invalid email or password.", 401

        return (
            "Login successful! Welcome, "
            + student["name"]
            + ". <a href='/jobs'>View Jobs</a>"
        )

    except mysql.connector.Error:
        app.logger.exception("Login error")
        return "Login failed. Check database connection.", 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# Registration page
@app.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    mobile = request.form.get("mobile", "").strip()
    department = request.form.get("department", "").strip()
    qualification = request.form.get("qualification", "").strip()
    password = request.form.get("password", "")

    if not all([name, email, mobile, department, qualification, password]):
        return "Please fill in all fields.", 400

    if len(password) < 8:
        return "Password must be at least 8 characters.", 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO students
            (name, email, mobile, department, qualification, password_hash)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            name, email, mobile, department, qualification,
            generate_password_hash(password)
        ))

        conn.commit()
        return "Registration successful! <a href='/login'>Login here</a>", 201

    except mysql.connector.IntegrityError:
        return "This email is already registered.", 409

    except mysql.connector.Error:
        app.logger.exception("Registration error")
        return "Registration failed. Check database connection.", 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# Jobs page
@app.route("/jobs")
def jobs_page():
    return render_template("jobs.html")


# View registered students
@app.route("/api/students")
def view_students():
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, name, email, mobile, department, qualification
            FROM students
            ORDER BY id DESC
        """)

        return jsonify(cursor.fetchall())

    except mysql.connector.Error:
        app.logger.exception("Could not load students")
        return jsonify({"message": "Could not load students"}), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# Registration API for index.html
@app.route("/api/register", methods=["POST"])
def register_student():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    mobile = data.get("mobile", "").strip()
    department = data.get("department", "").strip()
    qualification = data.get("qualification", "").strip()
    password = data.get("password", "")

    if not all([name, email, mobile, department, qualification, password]):
        return jsonify({
            "success": False,
            "message": "Please fill in all fields."
        }), 400

    if len(password) < 8:
        return jsonify({
            "success": False,
            "message": "Password must be at least 8 characters."
        }), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO students
            (name, email, mobile, department, qualification, password_hash)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            name, email, mobile, department, qualification,
            generate_password_hash(password)
        ))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Student registered successfully!"
        }), 201

    except mysql.connector.IntegrityError:
        return jsonify({
            "success": False,
            "message": "This email is already registered."
        }), 409

    except mysql.connector.Error:
        app.logger.exception("Registration database error")
        return jsonify({
            "success": False,
            "message": "Database connection or save failed."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# Login API for index.html
@app.route("/api/login", methods=["POST"])
def login_student():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Please enter email and password."
        }), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, name, password_hash
            FROM students
            WHERE email = %s
        """, (email,))

        student = cursor.fetchone()

        if (
            not student
            or not student["password_hash"]
            or not check_password_hash(student["password_hash"], password)
        ):
            return jsonify({
                "success": False,
                "message": "Invalid email or password."
            }), 401

        return jsonify({
            "success": True,
            "message": "Login successful! Welcome, " + student["name"] + "."
        }), 200

    except mysql.connector.Error:
        app.logger.exception("Login database error")
        return jsonify({
            "success": False,
            "message": "Could not complete login."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# Available jobs
JOBS = {
    "Software Developer": "ABC Technologies",
    "Web Developer": "Web Solutions",
    "Python Developer": "Tech Company"
}


# Apply for a job
@app.route("/apply/<job_title>", methods=["GET", "POST"])
def apply_job(job_title):
    if job_title not in JOBS:
        return "Job not found", 404

    company_name = JOBS[job_title]
    message = ""

    if request.method == "POST":
        email = request.form.get("email", "").strip()

        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT id FROM students WHERE email = %s",
                (email,)
            )
            student = cursor.fetchone()

            if not student:
                message = "This email is not registered."
            else:
                cursor.execute("""
                    INSERT INTO applications
                    (student_id, job_title, company_name)
                    VALUES (%s, %s, %s)
                """, (student["id"], job_title, company_name))

                conn.commit()
                message = "Application submitted successfully!"

        except mysql.connector.IntegrityError:
            if conn:
                conn.rollback()
            message = "You have already applied for this job."

        except mysql.connector.Error:
            if conn:
                conn.rollback()
            app.logger.exception("Application database error")
            message = "Could not submit application. Check applications table."

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    return render_template(
        "apply.html",
        job_title=job_title,
        company_name=company_name,
        message=message
    )


# View job applications
@app.route("/my-applications", methods=["GET", "POST"])
def my_applications():
    applications = []
    message = ""

    if request.method == "POST":
        email = request.form.get("email", "").strip()

        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT a.job_title, a.company_name, a.applied_at, a.status
                FROM applications a
                JOIN students s ON a.student_id = s.id
                WHERE s.email = %s
                ORDER BY a.applied_at DESC
            """, (email,))

            applications = cursor.fetchall()

            if not applications:
                message = "No applications found for this email."

        except mysql.connector.Error:
            app.logger.exception("Could not load applications")
            message = "Could not load applications."

        finally:
            if cursor:
                cursor.close()
            if conn and conn.is_connected():
                conn.close()

    return render_template(
        "my_applications.html",
        applications=applications,
        message=message
    )



# Reset password for an existing student
@app.route("/reset-student-password", methods=["GET", "POST"])
def reset_student_password():
    if request.method == "GET":
        return """
        <h2>Reset Student Password</h2>
        <form method="POST">
            <label>Email:</label>
            <input type="email" name="email" required>
            <br><br>
            <label>New Password:</label>
            <input type="password" name="password"
                   minlength="8" required>
            <br><br>
            <button type="submit">Save Password</button>
        </form>
        """

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if len(password) < 8:
        return "Password must be at least 8 characters.", 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE students
            SET password_hash = %s
            WHERE email = %s
        """, (generate_password_hash(password), email))

        if cursor.rowcount == 0:
            conn.rollback()
            return "Email not found.", 404

        conn.commit()
        return "Password updated successfully! <a href='/'>Go to Login</a>"

    except mysql.connector.Error:
        if conn:
            conn.rollback()
        app.logger.exception("Password reset error")
        return "Could not update password.", 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            # Start Flask server - keep this at the very end
if __name__ == "__main__":
    app.run(debug=True)