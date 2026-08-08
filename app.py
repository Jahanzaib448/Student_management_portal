from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import csv
from io import StringIO
import os
from flask import Response
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
try:
    from PIL import Image
except ImportError:
    Image = None

app = Flask(__name__)

app.config["SECRET_KEY"] = "9000"
# -----------------------------
# Database Configuration
# -----------------------------
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql+psycopg2://abc@localhost:5432/student_management_portal")

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Upload folder path
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static/uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Max file size: 2MB
MAX_CONTENT_LENGTH = 2 * 1024 * 1024

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

COURSE_MATERIAL_EXTENSIONS = {
    'pdf', 'mp4', 'avi', 'mov', 'mkv', 
    'ppt', 'pptx', 'doc', 'docx', 
    'jpg', 'jpeg', 'png', 'gif',
    'zip', 'rar', 'txt'
}

# Max file size: 500MB (for videos)
MAX_MATERIAL_SIZE = 500 * 1024 * 1024

# Allowed material types mapping
MATERIAL_TYPES = {
    'pdf': 'PDF Document',
    'mp4': 'Video',
    'avi': 'Video',
    'mov': 'Video',
    'mkv': 'Video',
    'ppt': 'PowerPoint',
    'pptx': 'PowerPoint',
    'doc': 'Word Document',
    'docx': 'Word Document',
    'jpg': 'Image',
    'jpeg': 'Image',
    'png': 'Image',
    'gif': 'Image',
    'zip': 'Archive',
    'rar': 'Archive',
    'txt': 'Text Document'
}

def get_material_type(filename):
    """Get material type from file extension"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return MATERIAL_TYPES.get(ext, 'Other')

# Course material upload folder
MATERIAL_UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static/uploads/materials')
os.makedirs(MATERIAL_UPLOAD_FOLDER, exist_ok=True)



# ============================================
# Login Required Decorator
# ============================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "danger")
            return redirect(url_for("login"))
        
        user = User.query.get(session["user_id"])
        if not user or user.role != 'admin':
            flash("❌ Admin access required. You are not authorized to view this page.", "danger")
            return redirect(url_for("dashboard"))
        
        return f(*args, **kwargs)
    return decorated_function

def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "danger")
            return redirect(url_for("login"))
        
        user = User.query.get(session["user_id"])
        if not user or user.role not in ['admin', 'teacher']:
            flash("❌ Teacher access required. You are not authorized to view this page.", "danger")
            return redirect(url_for("dashboard"))
        
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "danger")
            return redirect(url_for("login"))
        
        user = User.query.get(session["user_id"])
        if not user or user.role not in ['admin', 'teacher', 'student']:
            flash("❌ You are not authorized to view this page.", "danger")
            return redirect(url_for("dashboard"))
        
        return f(*args, **kwargs)
    return decorated_function

def teacher_or_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "danger")
            return redirect(url_for("login"))
        
        user = User.query.get(session["user_id"])
        if not user or user.role not in ['admin', 'teacher']:
            flash("❌ Teacher or Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# Models
# ============================================

# app.py mein User model update karein

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    
    # 👇 Role field add karein
    role = db.Column(db.String(20), nullable=False, default='student')
    # Values: 'admin', 'teacher', 'student'
    
    # Relationships
    students = db.relationship('Student', backref='owner', lazy=True, cascade="all, delete-orphan")
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_teacher(self):
        return self.role == 'teacher'
    
    def is_student(self):
        return self.role == 'student'
    
    def __repr__(self):
        return f"<User {self.username} ({self.role})>"
    
    profile_pic = db.Column(db.String(255), nullable=True, default='default.png')  # 👈 NEW
    
    def get_profile_pic(self):  # 👈 NEW
        if self.profile_pic and self.profile_pic != 'default.png':
            return url_for('static', filename=f'uploads/{self.profile_pic}')
        return url_for('static', filename='uploads/default.png')


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    course = db.Column(db.String(100), nullable=False)
    
    # Foreign Key to User
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f"<Student {self.student_name}>"
    
    # app.py mein Student model ke baad yeh code add karein

# ============================================
# Teacher Model - 🆕 NEW
# ============================================
class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    qualification = db.Column(db.String(200), nullable=False)
    joining_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Key to User (who created this teacher)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationship with User
    creator = db.relationship('User', backref='teachers', lazy=True)
    
    def __repr__(self):
        return f"<Teacher {self.teacher_name}>"
    
    # ============================================
# Course Model - 🆕 NEW
# ============================================
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(100), nullable=False)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    credit_hours = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.String(50), nullable=False)  # e.g., "16 weeks", "1 semester"
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign Key to User (who created this course)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Foreign Key to Teacher (assigned teacher)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=True)
    
    # Relationships
    creator = db.relationship('User', backref='courses', lazy=True)
    teacher = db.relationship('Teacher', backref='courses_teaching', lazy=True)
    
    # Many-to-Many with Students (through enrollment table)
    students = db.relationship('Student', secondary='enrollment', 
                               backref=db.backref('enrolled_courses', lazy=True))
    
    def __repr__(self):
        return f"<Course {self.course_code} - {self.course_name}>"

# ============================================
# Enrollment Association Table (Many-to-Many)
# ============================================
enrollment = db.Table('enrollment',
    db.Column('id', db.Integer, primary_key=True),
    db.Column('student_id', db.Integer, db.ForeignKey('student.id'), nullable=False),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), nullable=False),
    db.Column('enrollment_date', db.DateTime, default=datetime.utcnow),
    db.Column('grade', db.String(2), nullable=True)  # A, B, C, D, F
)

# ============================================
# Course Material Model - 🆕 NEW
# ============================================
# ============================================
# Course Material Model - 🆕 ADD THIS
# ============================================
class CourseMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    material_type = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    original_filename = db.Column(db.String(255), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    course = db.relationship('Course', backref='materials', lazy=True)
    user = db.relationship('User', backref='materials', lazy=True)
    
    def get_file_size_display(self):
        if not self.file_size:
            return 'Unknown'
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def get_file_icon(self):
        if self.material_type == 'PDF':
            return '📄'
        elif self.material_type in ['Video', 'MP4', 'MPEG']:
            return '🎬'
        elif self.material_type in ['PPT', 'PPTX']:
            return '📊'
        elif self.material_type in ['DOC', 'DOCX']:
            return '📝'
        elif self.material_type in ['Image', 'PNG', 'JPG', 'JPEG']:
            return '🖼️'
        else:
            return '📎'
    
    def __repr__(self):
        return f"<CourseMaterial {self.title}>"
# ============================================
# Attendance Model - 🆕 NEW
# ============================================
class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Student who is being marked
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    
    # Course for which attendance is being marked
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    
    # Date of attendance
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    
    # Status: Present, Absent, Late, Leave
    status = db.Column(db.String(20), nullable=False, default='Present')
    
    # Remarks (optional)
    remarks = db.Column(db.String(200), nullable=True)
    
    # Who marked this attendance
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Timestamp when record was created
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    student = db.relationship('Student', backref='attendances', lazy=True)
    course = db.relationship('Course', backref='attendances', lazy=True)
    user = db.relationship('User', backref='attendances', lazy=True)
    
    def __repr__(self):
        return f"<Attendance {self.student.student_name} - {self.date} - {self.status}>"

# ============================================
# Routes
# ============================================

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

# ============================================
# Registration
# ============================================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "student").strip()  # 👈 Get role from form
        
        # Required fields validation
        if not all([full_name, username, email, password]):
            flash("All fields are required.", "danger")
            return redirect(url_for("register"))
        
        # Password strength validation
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return redirect(url_for("register"))
        
        if not any(char.isdigit() for char in password):
            flash("Password must contain at least one number.", "danger")
            return redirect(url_for("register"))
        
        if not any(char.isupper() for char in password):
            flash("Password must contain at least one uppercase letter.", "danger")
            return redirect(url_for("register"))
        
        # Check duplicate username
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("register"))
        
        # Check duplicate email
        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")
            return redirect(url_for("register"))
        
        # 👇 Create user with selected role
        hashed_password = generate_password_hash(password)
        user = User(
            full_name=full_name,
            username=username,
            email=email,
            password=hashed_password,
            role=role  # 👈 Save role from form
        )
        
        db.session.add(user)
        db.session.commit()
        
        # 👇 Auto-create student/teacher record based on role
        if role == 'student':
            student = Student(
                student_name=full_name,
                email=email,
                age=18,  # Default age
                course='Not Assigned',
                user_id=user.id
            )
            db.session.add(student)
            
        elif role == 'teacher':
            teacher = Teacher(
                teacher_name=full_name,
                email=email,
                phone='Not Provided',
                specialization='Not Assigned',
                qualification='Not Assigned',
                user_id=user.id
            )
            db.session.add(teacher)
        
        db.session.commit()
        
        flash(f"Registration Successful! You are registered as {role}. Please login.", "success")
        return redirect(url_for("login"))
    
    return render_template("auth/register.html")
# ============================================
# Login
# ============================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()  # 👈 .lower() add karein
        password = request.form.get("password", "").strip()
        
        if not email or not password:
            flash("Email and Password are required.", "danger")
            return redirect(url_for("login"))
        
        # Email case-insensitive search
        user = User.query.filter(db.func.lower(User.email) == email).first()
        
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            
            flash(f"Login Successful! Welcome {user.role}!", "success")
            return redirect(url_for("dashboard"))
        
        flash("Invalid Email or Password!", "danger")
        return redirect(url_for("login"))
    
    return render_template("auth/login.html")# Logout
# ============================================
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for("login"))

# ============================================
# Students List with Pagination - ✅ FIXED
# ============================================
@app.route("/students")
@login_required
def students():
    try:
        user = User.query.get(session["user_id"])
        page = request.args.get('page', 1, type=int)
        per_page = 5
        
        # Role-based student fetching
        if user.role == 'admin':
            # Admin sees all students
            pagination = Student.query.order_by(
                Student.id.desc()
            ).paginate(page=page, per_page=per_page, error_out=False)
            
        elif user.role == 'teacher':
            # Teacher sees students in their courses
            teacher = Teacher.query.filter_by(user_id=user.id).first()
            if teacher:
                student_ids = []
                courses = Course.query.filter_by(teacher_id=teacher.id).all()
                for course in courses:
                    for student in course.students:
                        if student.id not in student_ids:
                            student_ids.append(student.id)
                
                if student_ids:
                    pagination = Student.query.filter(
                        Student.id.in_(student_ids)
                    ).order_by(Student.id.desc()).paginate(
                        page=page, per_page=per_page, error_out=False
                    )
                else:
                    pagination = None
            else:
                pagination = None
                
        else:  # Student role
            # Student sees only their own record
            student = Student.query.filter_by(user_id=user.id).first()
            if student:
                pagination = Student.query.filter_by(
                    id=student.id
                ).paginate(page=page, per_page=per_page, error_out=False)
            else:
                pagination = None
        
        # If no pagination object, show empty state
        if not pagination:
            return render_template("students/students.html", pagination=None)
        
        return render_template("students/students.html", pagination=pagination)
        
    except Exception as e:
        flash(f"Error loading students: {str(e)}", "danger")
        return render_template("students/students.html", pagination=None)
# ============================================
# Add Student
# ============================================
@app.route("/students/add", methods=["GET", "POST"])
@login_required
def add_student():
    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()
        email = request.form.get("email", "").strip()
        age = request.form.get("age", "").strip()
        course = request.form.get("course", "").strip()
        
        # Validation
        if not all([student_name, email, age, course]):
            flash("All fields are required.", "danger")
            return redirect(url_for("add_student"))
        
        try:
            age_int = int(age)
            if age_int <= 0 or age_int > 100:
                flash("Age must be between 1 and 100.", "danger")
                return redirect(url_for("add_student"))
        except ValueError:
            flash("Age must be a number.", "danger")
            return redirect(url_for("add_student"))
        
        # Check duplicate email
        if Student.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")
            return redirect(url_for("add_student"))
        
        # Create student with user_id
        student = Student(
            student_name=student_name,
            email=email,
            age=age_int,
            course=course,
            user_id=session["user_id"]
        )
        
        db.session.add(student)
        db.session.commit()
        
        flash("Student Saved Successfully!", "success")
        return redirect(url_for("students"))
    
    return render_template("students/add_student.html")

# ============================================
# Edit Student
# ============================================
@app.route("/students/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_student(id):
    student = Student.query.get_or_404(id)
    
    # Check ownership
    if student.user_id != session["user_id"]:
        flash("You are not authorized to edit this student.", "danger")
        return redirect(url_for("students"))
    
    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()
        email = request.form.get("email", "").strip()
        age = request.form.get("age", "").strip()
        course = request.form.get("course", "").strip()
        
        if not all([student_name, email, age, course]):
            flash("All fields are required.", "danger")
            return redirect(url_for("edit_student", id=id))
        
        try:
            age_int = int(age)
            if age_int < 16 or age_int > 100:
                flash("Age must be between 16 and 100.", "danger")
                return redirect(url_for("edit_student", id=id))
        except ValueError:
            flash("Age must be a number.", "danger")
            return redirect(url_for("edit_student", id=id))
        
        # Check duplicate email (excluding current student)
        existing = Student.query.filter_by(email=email).first()
        if existing and existing.id != student.id:
            flash("Email already exists.", "danger")
            return redirect(url_for("edit_student", id=id))
        
        # Update
        student.student_name = student_name
        student.email = email
        student.age = age_int
        student.course = course
        
        db.session.commit()
        flash("Student Updated Successfully!", "success")
        return redirect(url_for("students"))
    
    return render_template("students/edit_student.html", student=student)

# app.py mein add karein (after student routes)

# ============================================
# Teacher Routes - 🆕 NEW
# ============================================

# ---------- View All Teachers ----------
@app.route("/teachers")
@login_required
def teachers():
    try:
        user = User.query.get(session["user_id"])
        
        if user.role == 'admin':
            all_teachers = Teacher.query.all()
        elif user.role == 'teacher':
            all_teachers = Teacher.query.filter_by(user_id=user.id).all()
        else:
            all_teachers = []
        
        return render_template("teachers/teachers.html", teachers=all_teachers)
    except Exception as e:
        flash(f"Error loading teachers: {str(e)}", "danger")
        return render_template("teachers/teachers.html", teachers=[])
# ---------- Add Teacher ----------
@app.route("/teachers/add", methods=["GET", "POST"])
@login_required
def add_teacher():
    if request.method == "POST":
        teacher_name = request.form.get("teacher_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        specialization = request.form.get("specialization", "").strip()
        qualification = request.form.get("qualification", "").strip()
        
        # Validation
        if not all([teacher_name, email, phone, specialization, qualification]):
            flash("All fields are required.", "danger")
            return redirect(url_for("add_teacher"))
        
        # Check duplicate email
        if Teacher.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")
            return redirect(url_for("add_teacher"))
        
        # Create teacher
        teacher = Teacher(
            teacher_name=teacher_name,
            email=email,
            phone=phone,
            specialization=specialization,
            qualification=qualification,
            user_id=session["user_id"]
        )
        
        db.session.add(teacher)
        db.session.commit()
        
        flash(f"✅ Teacher '{teacher_name}' added successfully!", "success")
        return redirect(url_for("teachers"))
    
    return render_template("teachers/add_teacher.html")

# ============================================
# Course Routes - 🆕 NEW
# ============================================

# ---------- View All Courses ----------
@app.route("/courses")
@login_required
def courses():
    try:
        user = User.query.get(session["user_id"])
        
        # Admin aur Teacher sab courses dekh sakte hain
        if user.role in ['admin', 'teacher']:
            all_courses = Course.query.all()
        else:
            # Student sirf enrolled courses
            student = Student.query.filter_by(user_id=user.id).first()
            all_courses = student.enrolled_courses if student else []
        
        return render_template("courses/courses.html", courses=all_courses)
    except Exception as e:
        flash(f"Error loading courses: {str(e)}", "danger")
        return render_template("courses/courses.html", courses=[])
    # ---------- Add Course ----------
@app.route("/courses/add", methods=["GET", "POST"])
@login_required
def add_course():
    user = User.query.get(session["user_id"])
    
    # Sirf Admin aur Teacher course add kar sakte hain
    if user.role not in ['admin', 'teacher']:
        flash("❌ Only Admin and Teachers can add courses.", "danger")
        return redirect(url_for("courses"))
    
    # Get teachers for dropdown
    teachers = Teacher.query.all()
    
    if request.method == "POST":
        course_name = request.form.get("course_name", "").strip()
        course_code = request.form.get("course_code", "").strip()
        description = request.form.get("description", "").strip()
        credit_hours = request.form.get("credit_hours", "").strip()
        duration = request.form.get("duration", "").strip()
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()
        teacher_id = request.form.get("teacher_id", "").strip()
        
        # Validation
        if not all([course_name, course_code, credit_hours, duration, start_date, end_date]):
            flash("All fields are required.", "danger")
            return redirect(url_for("add_course"))
        
        # Check duplicate course code
        if Course.query.filter_by(course_code=course_code).first():
            flash("Course code already exists.", "danger")
            return redirect(url_for("add_course"))
        
        # Parse dates
        from datetime import datetime as dt
        try:
            start_date_obj = dt.strptime(start_date, "%Y-%m-%d")
            end_date_obj = dt.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            flash("Invalid date format. Use YYYY-MM-DD.", "danger")
            return redirect(url_for("add_course"))
        
        # Create course
        course = Course(
            course_name=course_name,
            course_code=course_code.upper(),
            description=description,
            credit_hours=int(credit_hours),
            duration=duration,
            start_date=start_date_obj,
            end_date=end_date_obj,
            user_id=session["user_id"],
            teacher_id=int(teacher_id) if teacher_id else None
        )
        
        db.session.add(course)
        db.session.commit()
        
        flash(f"✅ Course '{course_name}' added successfully!", "success")
        return redirect(url_for("courses"))
    
    # ✅ GET request ke liye return
    return render_template("courses/add_course.html", teachers=teachers)    # ... rest of code ...        # ... rest of code ...
# ---------- Edit Course ----------
@app.route("/courses/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_course(id):
    course = Course.query.get_or_404(id)
    teachers = Teacher.query.filter_by(user_id=session["user_id"]).all()
    
    # Check ownership
    if course.user_id != session["user_id"]:
        flash("You are not authorized to edit this course.", "danger")
        return redirect(url_for("courses"))
    
    if request.method == "POST":
        course_name = request.form.get("course_name", "").strip()
        course_code = request.form.get("course_code", "").strip()
        description = request.form.get("description", "").strip()
        credit_hours = request.form.get("credit_hours", "").strip()
        duration = request.form.get("duration", "").strip()
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()
        teacher_id = request.form.get("teacher_id", "").strip()
        
        if not all([course_name, course_code, credit_hours, duration, start_date, end_date]):
            flash("All fields are required.", "danger")
            return redirect(url_for("edit_course", id=id))
        
        # Check duplicate course code (excluding current course)
        existing = Course.query.filter_by(course_code=course_code).first()
        if existing and existing.id != course.id:
            flash("Course code already exists.", "danger")
            return redirect(url_for("edit_course", id=id))
        
        # Parse dates
        from datetime import datetime as dt
        try:
            start_date_obj = dt.strptime(start_date, "%Y-%m-%d")
            end_date_obj = dt.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            flash("Invalid date format. Use YYYY-MM-DD.", "danger")
            return redirect(url_for("edit_course", id=id))
        
        # Update course
        course.course_name = course_name
        course.course_code = course_code.upper()
        course.description = description
        course.credit_hours = int(credit_hours)
        course.duration = duration
        course.start_date = start_date_obj
        course.end_date = end_date_obj
        course.teacher_id = int(teacher_id) if teacher_id else None
        
        db.session.commit()
        
        flash(f"✅ Course '{course_name}' updated successfully!", "success")
        return redirect(url_for("courses"))
    
    return render_template("courses/edit_course.html", course=course, teachers=teachers)

# ---------- Delete Course ----------
@app.route("/courses/delete/<int:id>", methods=["POST"])
@login_required
def delete_course(id):
    course = Course.query.get_or_404(id)
    
    # Check ownership
    if course.user_id != session["user_id"]:
        flash("You are not authorized to delete this course.", "danger")
        return redirect(url_for("courses"))
    
    course_name = course.course_name
    db.session.delete(course)
    db.session.commit()
    
    flash(f"✅ Course '{course_name}' deleted successfully!", "success")
    return redirect(url_for("courses"))

# ---------- Course Detail ----------
@app.route("/courses/<int:id>")
@login_required
def course_detail(id):
    course = Course.query.get_or_404(id)
    user = User.query.get(session["user_id"])
    
    # 👑 Admin: Full access to all courses
    if user.role == 'admin':
        return render_template("courses/course_detail.html", course=course)
    
    # 👨‍🏫 Teacher: Only their assigned courses
    if user.role == 'teacher':
        teacher = Teacher.query.filter_by(user_id=user.id).first()
        if teacher and course.teacher_id == teacher.id:
            return render_template("courses/course_detail.html", course=course)
        else:
            flash("❌ You are not authorized to view this course.", "danger")
            return redirect(url_for("courses"))
    
    # 👨‍🎓 Student: Only enrolled courses
    if user.role == 'student':
        student = Student.query.filter_by(user_id=user.id).first()
        if student and course in student.enrolled_courses:
            return render_template("courses/course_detail.html", course=course)
        else:
            flash("❌ You are not authorized to view this course.", "danger")
            return redirect(url_for("courses"))
    
    flash("❌ You are not authorized to view this course.", "danger")
    return redirect(url_for("courses"))
# ---------- Enroll Student in Course ----------
@app.route("/courses/enroll/<int:course_id>", methods=["GET", "POST"])
@login_required
def enroll_student(course_id):
    course = Course.query.get_or_404(course_id)
    user = User.query.get(session["user_id"])
    
    # Check if user is admin or teacher (only they can enroll)
    if user.role not in ['admin', 'teacher']:
        flash("You are not authorized to enroll students.", "danger")
        return redirect(url_for("courses"))
    
    if request.method == "POST":
        student_id = request.form.get("student_id")
        student = Student.query.get_or_404(student_id)
        
        # Check if student already enrolled
        if student in course.students:
            flash(f"Student '{student.student_name}' is already enrolled in this course.", "warning")
        else:
            course.students.append(student)
            db.session.commit()
            flash(f"✅ Student '{student.student_name}' enrolled successfully!", "success")
        
        return redirect(url_for("course_detail", id=course_id))
    
    # ✅ FIXED: Get ALL students (not just current user's)
    enrolled_ids = [s.id for s in course.students]
    
    # 👇 ALL students (no user_id filter)
    if enrolled_ids:
        available_students = Student.query.filter(
            ~Student.id.in_(enrolled_ids)
        ).all()
    else:
        available_students = Student.query.all()
    
    return render_template(
        "courses/enroll_student.html", 
        course=course, 
        available_students=available_students
    )
# ---------- Remove Student from Course ----------
@app.route("/courses/remove/<int:course_id>/<int:student_id>", methods=["POST"])
@login_required
def remove_student(course_id, student_id):
    course = Course.query.get_or_404(course_id)
    student = Student.query.get_or_404(student_id)
    
    # Check ownership
    if course.user_id != session["user_id"]:
        flash("You are not authorized to remove students from this course.", "danger")
        return redirect(url_for("courses"))
    
    if student in course.students:
        course.students.remove(student)
        db.session.commit()
        flash(f"✅ Student '{student.student_name}' removed from course.", "success")
    else:
        flash(f"Student '{student.student_name}' is not enrolled in this course.", "warning")
    
    return redirect(url_for("course_detail", id=course_id))

# ---------- Edit Teacher ----------
@app.route("/teachers/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_teacher(id):
    teacher = Teacher.query.get_or_404(id)
    
    # Check ownership
    if teacher.user_id != session["user_id"]:
        flash("You are not authorized to edit this teacher.", "danger")
        return redirect(url_for("teachers"))
    
    if request.method == "POST":
        teacher_name = request.form.get("teacher_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        specialization = request.form.get("specialization", "").strip()
        qualification = request.form.get("qualification", "").strip()
        
        if not all([teacher_name, email, phone, specialization, qualification]):
            flash("All fields are required.", "danger")
            return redirect(url_for("edit_teacher", id=id))
        
        # Check duplicate email (excluding current teacher)
        existing = Teacher.query.filter_by(email=email).first()
        if existing and existing.id != teacher.id:
            flash("Email already exists.", "danger")
            return redirect(url_for("edit_teacher", id=id))
        
        # Update teacher
        teacher.teacher_name = teacher_name
        teacher.email = email
        teacher.phone = phone
        teacher.specialization = specialization
        teacher.qualification = qualification
        
        db.session.commit()
        
        flash(f"✅ Teacher '{teacher_name}' updated successfully!", "success")
        return redirect(url_for("teachers"))
    
    return render_template("teachers/edit_teacher.html", teacher=teacher)

# ---------- Delete Teacher ----------
@app.route("/teachers/delete/<int:id>", methods=["POST"])
@login_required
def delete_teacher(id):
    teacher = Teacher.query.get_or_404(id)
    
    # Check ownership
    if teacher.user_id != session["user_id"]:
        flash("You are not authorized to delete this teacher.", "danger")
        return redirect(url_for("teachers"))
    
    teacher_name = teacher.teacher_name
    db.session.delete(teacher)
    db.session.commit()
    
    flash(f"✅ Teacher '{teacher_name}' deleted successfully!", "success")
    return redirect(url_for("teachers"))

# ---------- Teacher Dashboard ----------

# ============================================
# Attendance Routes - 🆕 NEW
# ============================================

# ---------- Mark Attendance (Main Page) ----------
@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    user_id = session["user_id"]
    
    # Get all courses for dropdown
    courses = Course.query.filter_by(user_id=user_id).all()
    
    # Default to first course if exists
    selected_course_id = request.args.get('course_id', type=int)
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    if not selected_course_id and courses:
        selected_course_id = courses[0].id
    
    # Get students for selected course
    selected_course = None
    students = []
    attendance_records = {}
    
    if selected_course_id:
        selected_course = Course.query.get(selected_course_id)
        if selected_course:
            students = selected_course.students
    
    # Get existing attendance for this date
    if selected_course_id and selected_date:
        existing_attendance = Attendance.query.filter_by(
            course_id=selected_course_id,
            date=datetime.strptime(selected_date, '%Y-%m-%d').date(),
            user_id=user_id
        ).all()
        
        # Create a dict for quick lookup
        for att in existing_attendance:
            attendance_records[att.student_id] = att.status
    
    if request.method == "POST":
        course_id = request.form.get('course_id', type=int)
        date_str = request.form.get('date')
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Get all students in this course
        course = Course.query.get(course_id)
        if not course:
            flash("Course not found.", "danger")
            return redirect(url_for('attendance'))
        
        # Process each student's attendance
        for student in course.students:
            status = request.form.get(f'status_{student.id}', 'Absent')
            remarks = request.form.get(f'remarks_{student.id}', '')
            
            # Check if attendance already exists
            existing = Attendance.query.filter_by(
                student_id=student.id,
                course_id=course_id,
                date=date_obj,
                user_id=user_id
            ).first()
            
            if existing:
                # Update existing record
                existing.status = status
                existing.remarks = remarks
            else:
                # Create new record
                attendance = Attendance(
                    student_id=student.id,
                    course_id=course_id,
                    date=date_obj,
                    status=status,
                    remarks=remarks,
                    user_id=user_id
                )
                db.session.add(attendance)
        
        db.session.commit()
        flash("✅ Attendance saved successfully!", "success")
        return redirect(url_for('attendance', course_id=course_id, date=date_str))
    
    return render_template(
        "attendance/attendance.html",
        courses=courses,
        selected_course=selected_course,
        selected_course_id=selected_course_id,
        selected_date=selected_date,
        students=students,
        attendance_records=attendance_records
    )

# ---------- View Attendance Report ----------
@app.route("/attendance/report")
@login_required
def attendance_report():
    user_id = session["user_id"]
    
    # Get filter parameters
    course_id = request.args.get('course_id', type=int)
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    student_id = request.args.get('student_id', type=int)
    
    # Default to current month
    if not month:
        month = datetime.now().month
    if not year:
        year = datetime.now().year
    
    # Get all courses for dropdown
    courses = Course.query.filter_by(user_id=user_id).all()
    
    # Build query
    query = Attendance.query.filter_by(user_id=user_id)
    
    if course_id:
        query = query.filter_by(course_id=course_id)
    
    if month and year:
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()
        query = query.filter(Attendance.date >= start_date, Attendance.date < end_date)
    
    if student_id:
        query = query.filter_by(student_id=student_id)
    
    attendances = query.order_by(Attendance.date.desc()).all()
    
    # Calculate statistics
    total_days = len(set([a.date for a in attendances]))
    present_count = len([a for a in attendances if a.status == 'Present'])
    absent_count = len([a for a in attendances if a.status == 'Absent'])
    late_count = len([a for a in attendances if a.status == 'Late'])
    leave_count = len([a for a in attendances if a.status == 'Leave'])
    
    # Get all students for dropdown
    students = Student.query.filter_by(user_id=user_id).all()
    
    return render_template(
        "attendance/report.html",
        courses=courses,
        students=students,
        attendances=attendances,
        total_days=total_days,
        present_count=present_count,
        absent_count=absent_count,
        late_count=late_count,
        leave_count=leave_count,
        selected_course=course_id,
        selected_month=month,
        selected_year=year,
        selected_student=student_id
    )

# ---------- Student Attendance Stats ----------
@app.route("/attendance/student/<int:student_id>")
@login_required
def student_attendance_stats(student_id):
    user_id = session["user_id"]
    
    student = Student.query.get_or_404(student_id)
    
    # Check ownership
    if student.user_id != user_id:
        flash("You are not authorized to view this student's attendance.", "danger")
        return redirect(url_for('attendance_report'))
    
    # Get all attendance records for this student
    attendances = Attendance.query.filter_by(
        student_id=student_id,
        user_id=user_id
    ).all()
    
    # Calculate statistics
    total = len(attendances)
    present = len([a for a in attendances if a.status == 'Present'])
    absent = len([a for a in attendances if a.status == 'Absent'])
    late = len([a for a in attendances if a.status == 'Late'])
    leave = len([a for a in attendances if a.status == 'Leave'])
    
    # Calculate percentage
    percentage = (present / total * 100) if total > 0 else 0
    
    # Get course-wise stats
    course_stats = []
    courses = set([a.course_id for a in attendances])
    for course_id in courses:
        course_attendances = [a for a in attendances if a.course_id == course_id]
        course = Course.query.get(course_id)
        course_present = len([a for a in course_attendances if a.status == 'Present'])
        course_total = len(course_attendances)
        course_stats.append({
            'course_name': course.course_name if course else 'Unknown',
            'present': course_present,
            'total': course_total,
            'percentage': (course_present / course_total * 100) if course_total > 0 else 0
        })
    
    return render_template(
        "attendance/student_stats.html",
        student=student,
        total=total,
        present=present,
        absent=absent,
        late=late,
        leave=leave,
        percentage=round(percentage, 1),
        course_stats=course_stats,
        attendances=attendances
    )

# ============================================
# Delete Student
# ============================================
@app.route("/students/delete/<int:id>", methods=["POST"])
@login_required
def delete_student(id):
    student = Student.query.get_or_404(id)
    
    # Check ownership
    if student.user_id != session["user_id"]:
        flash("You are not authorized to delete this student.", "danger")
        return redirect(url_for("students"))
    
    db.session.delete(student)
    db.session.commit()
    flash("Student deleted successfully!", "success")
    return redirect(url_for("students"))

# ============================================
# Dashboard
# ============================================
# ============================================
# Dashboard - Role Based Redirect
# ============================================
# ============================================
# Dashboard - Role Based Redirect
# ============================================
@app.route("/dashboard")
@login_required
def dashboard():
    user = User.query.get(session["user_id"])
    
    if user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif user.role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    elif user.role == 'student':
        return redirect(url_for('student_dashboard'))
    else:
        flash("Invalid user role.", "danger")
        return redirect(url_for('home'))

# ============================================
# Admin Dashboard
# ============================================
@app.route("/admin/dashboard")
@login_required
@admin_required
def admin_dashboard():
    user = User.query.get(session["user_id"])
    
    total_students = Student.query.count()
    total_teachers = Teacher.query.count()
    total_courses = Course.query.count()
    total_users = User.query.count()
    
    # 🔥 Naya Data: Course Statistics (Format: [['Course A', 5], ['Course B', 10]])
    courses = Course.query.all()
    course_stats = []
    for course in courses:
        student_count = len(course.students)
        if student_count > 0:
            course_stats.append([course.course_name, student_count])
            
    # 🔥 Naya Data: Age Statistics (Format: [['18', 10], ['19', 5]])
    age_stats = []
    students = Student.query.all()
    age_count = {}
    for student in students:
        age_count[student.age] = age_count.get(student.age, 0) + 1
    for age, count in sorted(age_count.items()):
        age_stats.append([str(age), count])
    
    recent_students = Student.query.order_by(Student.id.desc()).limit(5).all()
    recent_teachers = Teacher.query.order_by(Teacher.id.desc()).limit(5).all()
    recent_courses = Course.query.order_by(Course.id.desc()).limit(5).all()
    
    return render_template(
        "admin/dashboard.html",
        user=user,
        total_students=total_students,
        total_teachers=total_teachers,
        total_courses=total_courses,
        total_users=total_users,
        recent_students=recent_students,
        recent_teachers=recent_teachers,
        recent_courses=recent_courses,
        # 🔥 Yeh variable pass kar rahe hain:
        course_stats=course_stats,
        age_stats=age_stats
    )# ============================================
# Admin: Manage Users
# ============================================
@app.route("/admin/users")
@login_required
@admin_required
def admin_users():
    users = User.query.all()
    return render_template("admin/users.html", users=users)

# ============================================
# Admin: Change User Role
# ============================================
@app.route("/admin/users/role/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def admin_change_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get("role")
    
    if new_role in ['admin', 'teacher', 'student']:
        user.role = new_role
        db.session.commit()
        flash(f"✅ User '{user.username}' role changed to '{new_role}'.", "success")
    else:
        flash("❌ Invalid role.", "danger")
    
    return redirect(url_for('admin_users'))

# ============================================
# Teacher Dashboard - ✅ KEEP THIS
# ============================================
@app.route("/teacher/dashboard")
@login_required
@teacher_required
def teacher_dashboard():
    user = User.query.get(session["user_id"])
    
    teacher = Teacher.query.filter_by(user_id=user.id).first()
    
    # 👇 Teacher ke assigned courses
    if teacher:
        my_courses = Course.query.filter_by(teacher_id=teacher.id).all()
    else:
        my_courses = []
    
    # 👇 Teacher ke courses ke students
    students = []
    for course in my_courses:
        students.extend(course.students)
    students = list(set(students))
    
    return render_template(
        "teacher/dashboard.html",
        user=user,
        teacher=teacher,
        my_courses=my_courses,
        students=students,
        total_students=len(students),
        total_courses=len(my_courses)
    )
# ============================================
# Student Dashboard
# ============================================
@app.route("/student/dashboard")
@login_required
def student_dashboard():
    user = User.query.get(session["user_id"])
    
    # Check if user is student, otherwise redirect
    if user.role != 'student':
        if user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user.role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
        else:
            flash("Invalid user role.", "danger")
            return redirect(url_for('home'))
    
    # Get student record
    student = Student.query.filter_by(user_id=user.id).first()
    
    if not student:
        flash("Student record not found. Please contact admin.", "warning")
        return render_template("student/dashboard.html", user=user, student=None)
    
    # Get student's enrolled courses
    my_courses = student.enrolled_courses if student else []
    
    # Get student's attendance
    attendances = Attendance.query.filter_by(student_id=student.id if student else 0).all()
    total_attendance = len(attendances)
    present_attendance = len([a for a in attendances if a.status == 'Present'])
    attendance_percentage = (present_attendance / total_attendance * 100) if total_attendance > 0 else 0
    
    return render_template(
        "student/dashboard.html",
        user=user,
        student=student,
        my_courses=my_courses,
        total_courses=len(my_courses),
        total_attendance=total_attendance,
        attendance_percentage=round(attendance_percentage, 1)
    )# ---------- My Courses (Student/Teacher) ----------
@app.route("/my-courses")
@login_required
def my_courses():
    user = User.query.get(session["user_id"])
    
    if user.role == 'student':
        student = Student.query.filter_by(user_id=user.id).first()
        if student:
            courses = student.enrolled_courses
        else:
            courses = []
        return render_template("my_courses.html", courses=courses, role='student')
    
    elif user.role == 'teacher':
        teacher = Teacher.query.filter_by(user_id=user.id).first()
        if teacher:
            courses = Course.query.filter_by(teacher_id=teacher.id).all()
        else:
            courses = []
        return render_template("my_courses.html", courses=courses, role='teacher')
    
    else:
        flash("Access denied.", "danger")
        return redirect(url_for("dashboard"))

# ---------- My Attendance (Student) ----------
@app.route("/my-attendance")
@login_required
def my_attendance():
    user = User.query.get(session["user_id"])
    
    if user.role != 'student':
        flash("Only students can view attendance.", "warning")
        return redirect(url_for("dashboard"))
    
    student = Student.query.filter_by(user_id=user.id).first()
    if not student:
        flash("Student record not found.", "danger")
        return redirect(url_for("dashboard"))
    
    attendances = Attendance.query.filter_by(student_id=student.id).all()
    
    # Calculate statistics
    total = len(attendances)
    present = len([a for a in attendances if a.status == 'Present'])
    absent = len([a for a in attendances if a.status == 'Absent'])
    late = len([a for a in attendances if a.status == 'Late'])
    leave = len([a for a in attendances if a.status == 'Leave'])
    percentage = (present / total * 100) if total > 0 else 0
    
    return render_template(
        "student/attendance.html",
        student=student,
        attendances=attendances,
        total=total,
        present=present,
        absent=absent,
        late=late,
        leave=leave,
        percentage=round(percentage, 1)
    )
    # ============================================
@app.route("/students/search", methods=["GET"])
@login_required
def search_students():
    # Get search query from URL
    query = request.args.get('q', '').strip()
    
    if query:
        # Search in name, email, and course
        students = Student.query.filter(
            (Student.student_name.contains(query)) |
            (Student.email.contains(query)) |
            (Student.course.contains(query)),
            Student.user_id == session["user_id"]
        ).all()
    else:
        students = []
    
    return render_template("students/search.html", 
                          students=students, 
                          query=query)

# ============================================
# Profile
# ============================================
# ============================================
# Profile - ❌ OLD CODE (Replace this)
# ============================================
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = User.query.get(session["user_id"])
    
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        
        if not full_name or not email:
            flash("All fields are required.", "danger")
            return redirect(url_for("profile"))
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user.id:
            flash("Email already exists.", "danger")
            return redirect(url_for("profile"))
        
        user.full_name = full_name
        user.email = email
        db.session.commit()
        
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))
    
    total_students = Student.query.filter_by(user_id=user.id).count()
    total_courses = db.session.query(Student.course).filter_by(user_id=user.id).distinct().count()
    
    return render_template("profile/profile.html", 
                          user=user,
                          total_students=total_students,
                          total_courses=total_courses)# ============================================
# Change Password
# ============================================
@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        
        user = User.query.get(session["user_id"])
        
        # Check current password
        if not check_password_hash(user.password, current_password):
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("change_password"))
        
        # Check if passwords match
        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("change_password"))
        
        # Check password strength
        if len(new_password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return redirect(url_for("change_password"))
        
        if not any(char.isdigit() for char in new_password):
            flash("Password must contain at least one number.", "danger")
            return redirect(url_for("change_password"))
        
        if not any(char.isupper() for char in new_password):
            flash("Password must contain at least one uppercase letter.", "danger")
            return redirect(url_for("change_password"))
        
        # Update password
        user.password = generate_password_hash(new_password)
        db.session.commit()
        
        flash("Password changed successfully!", "success")
        return redirect(url_for("profile"))
    
    # ✅ FIXED: Sahi path with folder
    return render_template("profile/change_password.html")
# ============================================
# Export to CSV
# ============================================
@app.route("/students/export/csv")
@login_required
def export_csv():
    # Get all students for current user
    students = Student.query.filter_by(user_id=session["user_id"]).all()
    
    # Create CSV in memory
    si = StringIO()
    cw = csv.writer(si)
    
    # Write header
    cw.writerow(['ID', 'Name', 'Email', 'Age', 'Course'])
    
    # Write data
    for student in students:
        cw.writerow([
            student.id,
            student.student_name,
            student.email,
            student.age,
            student.course
        ])
    
    # Get CSV content
    output = si.getvalue()
    
    # Return as downloadable file
    return Response(
        output,
        mimetype='text/csv',
        headers={
            "Content-Disposition": "attachment;filename=students_export.csv"
        }
    )

# ============================================
# Course Material Routes - 🆕 NEW
# ============================================

# ---------- View Course Materials ----------
# ============================================
# Course Material Routes - 🆕 ADD THIS
# ============================================

# ---------- View Course Materials ----------
@app.route("/course/<int:course_id>/materials")
@login_required
def course_materials(course_id):
    course = Course.query.get_or_404(course_id)
    materials = CourseMaterial.query.filter_by(course_id=course_id).all()
    
    return render_template(
        "materials/materials.html",
        course=course,
        materials=materials
    )

# ---------- Upload Course Material ----------
@app.route("/course/<int:course_id>/materials/upload", methods=["GET", "POST"])
@login_required
def upload_material(course_id):
    course = Course.query.get_or_404(course_id)
    user = User.query.get(session["user_id"])
    
    # Only Admin, Teacher, or course creator can upload
    if user.role not in ['admin', 'teacher'] and course.user_id != user.id:
        flash("❌ You are not authorized to upload materials for this course.", "danger")
        return redirect(url_for('course_detail', id=course_id))
    
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        
        if not title:
            flash("⚠️ Title is required.", "danger")
            return redirect(url_for('upload_material', course_id=course_id))
        
        if 'file' not in request.files:
            flash("⚠️ Please select a file.", "danger")
            return redirect(url_for('upload_material', course_id=course_id))
        
        file = request.files['file']
        
        if file.filename == '':
            flash("⚠️ Please select a file.", "danger")
            return redirect(url_for('upload_material', course_id=course_id))
        
        # Check file extension
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if ext not in COURSE_MATERIAL_EXTENSIONS:
            flash(f"❌ File type .{ext} is not allowed. Allowed: PDF, MP4, PPT, DOC, etc.", "danger")
            return redirect(url_for('upload_material', course_id=course_id))
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_MATERIAL_SIZE:
            flash(f"❌ File size exceeds 500MB limit.", "danger")
            return redirect(url_for('upload_material', course_id=course_id))
        
        # Save file
        filename = secure_filename(file.filename)
        timestamp = int(datetime.now().timestamp())
        new_filename = f"{course_id}_{timestamp}_{filename}"
        file_path = os.path.join(MATERIAL_UPLOAD_FOLDER, new_filename)
        
        file.save(file_path)
        
        # Create material record
        material = CourseMaterial(
            title=title,
            description=description,
            material_type=get_material_type(filename).upper(),
            file_path=f"uploads/materials/{new_filename}",
            file_size=file_size,
            original_filename=filename,
            course_id=course_id,
            user_id=session["user_id"]
        )
        
        db.session.add(material)
        db.session.commit()
        
        flash(f"✅ Material '{title}' uploaded successfully!", "success")
        return redirect(url_for('course_materials', course_id=course_id))
    
    return render_template("materials/upload_material.html", course=course)

# ---------- Download Material ----------
@app.route("/materials/download/<int:material_id>")
@login_required
def download_material(material_id):
    material = CourseMaterial.query.get_or_404(material_id)
    from flask import send_file
    
    # Check if user has access
    user = User.query.get(session["user_id"])
    course = Course.query.get(material.course_id)
    
    if user.role not in ['admin', 'teacher']:
        # Check if student is enrolled
        student = Student.query.filter_by(user_id=user.id).first()
        if not student or course not in student.enrolled_courses:
            flash("❌ You are not enrolled in this course.", "danger")
            return redirect(url_for('home'))
    
    file_path = os.path.join(os.getcwd(), 'static', material.file_path)
    
    if not os.path.exists(file_path):
        flash("❌ File not found.", "danger")
        return redirect(url_for('course_materials', course_id=material.course_id))
    
    return send_file(file_path, as_attachment=True, download_name=material.original_filename)

# ---------- Delete Material ----------
@app.route("/materials/delete/<int:material_id>", methods=["POST"])
@login_required
def delete_material(material_id):
    material = CourseMaterial.query.get_or_404(material_id)
    user = User.query.get(session["user_id"])
    
    # Only Admin or material uploader can delete
    if user.role != 'admin' and material.user_id != user.id:
        flash("❌ You are not authorized to delete this material.", "danger")
        return redirect(url_for('course_materials', course_id=material.course_id))
    
    # Delete file from system
    file_path = os.path.join(os.getcwd(), 'static', material.file_path)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except:
            pass
    
    db.session.delete(material)
    db.session.commit()
    
    flash(f"✅ Material deleted successfully!", "success")
    return redirect(url_for('course_materials', course_id=material.course_id))# ============================================
# Create Database Tables
# ============================================
with app.app_context():
    db.create_all()
    print("✅ Database tables created/verified!")

if __name__ == "__main__":
    app.run(debug=True)