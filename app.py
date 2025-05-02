from flask import Flask, render_template, request, redirect, session, flash, send_file, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import matplotlib.pyplot as plt
import os
import math
from flask_migrate import Migrate
from datetime import datetime, timedelta, timezone
import pytz
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this for production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'  # Your database URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Define User class with UserMixin
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)  # This stores the email
    password = db.Column(db.String(150), nullable=False)
    profile_image = db.Column(db.String(255), nullable=False, default='default_profile.png')
    subjects = db.relationship('Subject', backref='owner', lazy=True)
    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    likes = db.relationship('Like', backref='user', lazy=True)
    notes = db.relationship('Note', backref='author', lazy=True)
    
    @property
    def get_profile_image(self):
        return self.profile_image if self.profile_image else 'default_profile.png'

# Load user function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    attended = db.Column(db.Integer, default=0)
    missed = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True)
    likes = db.relationship('Like', backref='post', lazy=True)

    @property
    def local_timestamp(self):
        """Convert UTC timestamp to IST"""
        utc_time = self.timestamp.replace(tzinfo=timezone.utc)
        return utc_time.astimezone(ist)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    @property
    def local_timestamp(self):
        """Convert UTC timestamp to IST"""
        utc_time = self.timestamp.replace(tzinfo=timezone.utc)
        return utc_time.astimezone(ist)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Add IST timezone
ist = pytz.timezone('Asia/Kolkata')

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    file_path = db.Column(db.String(255))
    file_name = db.Column(db.String(255))
    file_type = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def local_time(self):
        """Convert UTC time to IST"""
        if self.updated_at is None:
            return None
        utc_time = self.updated_at.replace(tzinfo=timezone.utc)
        return utc_time.astimezone(ist)

# Add IST timezone
ist = pytz.timezone('Asia/Kolkata')

# ------------------ UTILITY FUNCTIONS ------------------

def calculate_attendance_stats(user_id):
    subjects = Subject.query.filter_by(user_id=user_id).all()
    stats = {}
    for subject in subjects:
        attended = subject.attended
        missed = subject.missed
        total = subject.total
        current_classes = attended + missed
        percentage = (attended / total * 100) if total > 0 else 0
        
        # Calculate minimum classes needed for 75% attendance
        min_required = math.ceil(0.75 * total)
        remaining_classes = total - current_classes
        
        if percentage >= 75:
            message = "On track"
        else:
            # Check if it's still possible to achieve 75%
            max_possible_attendance = attended + remaining_classes
            max_possible_percentage = (max_possible_attendance / total * 100)
            
            if max_possible_percentage < 75:
                message = "Cannot achieve 75% attendance"
            else:
                needed_to_reach = min_required - attended
                message = f"Need {needed_to_reach} more classes"
        
        stats[subject.name] = {
            'id': subject.id,
            'attended': attended,
            'missed': missed,
            'total': total,
            'percentage': round(percentage, 1),
            'message': message,
            'classes_left': remaining_classes
        }
    return stats

def allowed_file(filename, allowed_extensions=None):
    if allowed_extensions is None:
        allowed_extensions = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'ppt', 'pptx'}
    if not filename:
        return False
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------ ROUTES ------------------

@app.route("/")
def home():
    if current_user.is_authenticated:
        stats = calculate_attendance_stats(current_user.id)
        return render_template("index.html", subjects=stats, active_page='attendance')  # If logged in, show attendance
    else:
        return render_template("front.html")  # If not logged in, show the front page

@app.route("/social")
@login_required
def social_dashboard():
    # Get posts with author and comment information
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    for post in posts:
        if post.image_path:
            # Make sure image path is relative to static folder
            post.image_path = post.image_path.replace('\\', '/')
    return render_template("dashboard.html", posts=posts, active_page='social')

@app.route("/create_post", methods=["POST"])
@login_required
def create_post():
    content = request.form.get('content', '').strip()
    image = request.files.get('image')
    image_path = None
    
    # Allow posts with either content or image or both
    if not content and not image:
        flash('Please add some content or an image to post', 'warning')
        return redirect(url_for('social_dashboard'))
    
    if image and image.filename and allowed_file(image.filename):
        filename = secure_filename(image.filename)
        # Use current IST time for filename
        current_time = datetime.now(ist)
        timestamp = current_time.strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        image_path = os.path.join('uploads', filename)
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(full_path)
    
    # Create post with current IST time converted to UTC for storage
    current_time = datetime.now(ist)
    utc_time = current_time.astimezone(timezone.utc)
    post = Post(content=content, image_path=image_path, user_id=current_user.id, timestamp=utc_time)
    db.session.add(post)
    db.session.commit()
    
    return redirect(url_for('social_dashboard'))

@app.route("/like_post/<int:post_id>", methods=["POST"])
@login_required
def like_post(post_id):
    existing_like = Like.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first()
    
    if existing_like:
        db.session.delete(existing_like)
    else:
        like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(like)
    
    db.session.commit()
    return redirect(url_for('social_dashboard'))

@app.route("/add_comment/<int:post_id>", methods=["POST"])
@login_required
def add_comment(post_id):
    content = request.form.get('content')
    if content:
        # Create comment with current IST time converted to UTC for storage
        current_time = datetime.now(ist)
        utc_time = current_time.astimezone(timezone.utc)
        comment = Comment(content=content, user_id=current_user.id, post_id=post_id, timestamp=utc_time)
        db.session.add(comment)
        db.session.commit()
    return redirect(url_for('social_dashboard'))

@app.route("/delete_post/<int:post_id>", methods=["POST"])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id != current_user.id:
        flash("You can't delete someone else's post!", "danger")
        return redirect(url_for('social_dashboard'))
    
    # Delete associated comments first
    Comment.query.filter_by(post_id=post_id).delete()
    
    # Delete associated likes
    Like.query.filter_by(post_id=post_id).delete()
    
    # Delete associated image if exists
    if post.image_path:
        image_file = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(post.image_path))
        if os.path.exists(image_file):
            os.remove(image_file)
    
    # Finally delete the post
    db.session.delete(post)
    db.session.commit()
    
    return redirect(url_for('social_dashboard'))

@app.route("/delete_subject/<int:subject_id>", methods=["POST"])
@login_required
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    if subject.user_id != current_user.id:
        flash("You cannot delete this subject!", "danger")
        return redirect("/")
    
    db.session.delete(subject)
    db.session.commit()
    flash("Subject deleted successfully", "success")
    return redirect("/")

@app.route("/fix_timestamps")
@login_required
def fix_timestamps():
    # Fix post timestamps
    posts = Post.query.all()
    for post in posts:
        # Convert naive UTC datetime to aware UTC datetime
        if post.timestamp.tzinfo is None:
            aware_utc = post.timestamp.replace(tzinfo=timezone.utc)
            # Convert to IST
            ist_time = aware_utc.astimezone(ist)
            # Store back as UTC
            post.timestamp = ist_time.astimezone(timezone.utc)
    
    # Fix comment timestamps
    comments = Comment.query.all()
    for comment in comments:
        if comment.timestamp.tzinfo is None:
            aware_utc = comment.timestamp.replace(tzinfo=timezone.utc)
            ist_time = aware_utc.astimezone(ist)
            comment.timestamp = ist_time.astimezone(timezone.utc)
    
    db.session.commit()
    flash('All timestamps have been updated to correct timezone', 'success')
    return redirect(url_for('social_dashboard'))

@app.template_filter('has_liked')
def has_liked(post, user_id):
    return any(like.user_id == user_id for like in post.likes)

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Check if email is college email
        if not username.endswith("@nitdelhi.ac.in"):
            flash("Please use your college email ID (.......@nitdelhi.ac.in)", "warning")
            return redirect(url_for('login'))

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully", "info")
    return redirect(url_for('home'))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please fill in all fields', 'danger')
            return redirect(url_for('register'))
        
        # Check if email is college email
        if not username.endswith("@nitdelhi.ac.in"):
            flash("Please use your college email ID (.......@nitdelhi.ac.in)", "warning")
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route("/add_subject", methods=["POST"])
@login_required
def add_subject():
    name = request.form["subject"]
    total = int(request.form["total_classes"])
    subject = Subject(name=name, total=total, attended=0, user_id=current_user.id)
    db.session.add(subject)
    db.session.commit()
    return redirect("/")

@app.route("/update_attendance", methods=["POST"])
@login_required
def update_attendance():
    subject = Subject.query.filter_by(name=request.form["subject"], user_id=current_user.id).first()
    if subject:
        current_classes = subject.attended + subject.missed
        
        # Only allow updates if we haven't reached total classes
        if current_classes < subject.total:
            if request.form["action"] == "attended":
                # Check if adding one more attended class would exceed total
                if current_classes + 1 <= subject.total:
                    subject.attended += 1
                else:
                    flash("Cannot exceed total number of classes", "warning")
            elif request.form["action"] == "missed":
                # Check if adding one more missed class would exceed total
                if current_classes + 1 <= subject.total:
                    subject.missed += 1
                else:
                    flash("Cannot exceed total number of classes", "warning")
            db.session.commit()
        else:
            flash("Cannot update attendance: Total classes limit reached", "warning")
    return redirect("/")

@app.route("/plot.png")
@login_required
def plot():
    subjects = Subject.query.filter_by(user_id=current_user.id).all()
    names = [s.name for s in subjects]
    percentages = [(s.attended / s.total) * 100 if s.total else 0 for s in subjects]

    plt.figure(figsize=(10, 5))
    plt.bar(names, percentages, color='skyblue')
    plt.ylabel("Attendance %")
    plt.title("Attendance Overview")
    plt.ylim(0, 100)
    plt.tight_layout()

    if not os.path.exists('static'):
        os.makedirs('static')
    plt.savefig("static/plot.png")
    plt.close()
    return send_file("static/plot.png", mimetype='image/png')

@app.route('/notes')
@login_required
def notes_dashboard():
    all_notes = Note.query.order_by(Note.updated_at.desc()).all()
    return render_template('notes.html', notes=all_notes, current_user=current_user, active_page='notes')

@app.route('/notes/new', methods=['GET', 'POST'])
@login_required
def new_note():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content', '')
        file = request.files.get('file')
        
        if not title:
            flash('Title is required', 'danger')
            return redirect(url_for('new_note'))
        
        note = Note(title=title, user_id=current_user.id)
        
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join('uploads', 'notes', filename)
            full_path = os.path.join(app.static_folder, file_path)
            
            # Ensure the upload directory exists
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Save the file
            file.save(full_path)
            
            # Store file information
            note.file_path = file_path
            note.file_name = filename
            note.file_type = os.path.splitext(filename)[1][1:].lower()
        
        db.session.add(note)
        db.session.commit()
        flash('Assignment uploaded successfully!', 'success')
        return redirect(url_for('notes_dashboard'))
    
    return render_template('new_note.html', active_page='notes')

@app.route('/notes/<int:note_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id:
        flash('You do not have permission to edit this assignment', 'danger')
        return redirect(url_for('notes_dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content', '')
        file = request.files.get('file')
        
        if not title:
            flash('Title is required', 'danger')
            return redirect(url_for('edit_note', note_id=note_id))
        
        note.title = title
        
        if file and file.filename:
            # Delete old file if it exists
            if note.file_path:
                old_file_path = os.path.join(app.static_folder, note.file_path)
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
            
            # Save new file
            filename = secure_filename(file.filename)
            file_path = os.path.join('uploads', 'notes', filename)
            full_path = os.path.join(app.static_folder, file_path)
            
            # Ensure the upload directory exists
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Save the file
            file.save(full_path)
            
            # Update file information
            note.file_path = file_path
            note.file_name = filename
            note.file_type = os.path.splitext(filename)[1][1:].lower()
        
        db.session.commit()
        flash('Assignment updated successfully!', 'success')
        return redirect(url_for('notes_dashboard'))
    
    return render_template('edit_note.html', note=note, active_page='notes')

@app.route('/notes/<int:note_id>/delete', methods=['POST'])
@login_required
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id:
        flash('You do not have permission to delete this assignment', 'danger')
        return redirect(url_for('notes_dashboard'))
    
    # Delete the file if it exists
    if note.file_path:
        file_path = os.path.join(app.static_folder, note.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    db.session.delete(note)
    db.session.commit()
    flash('Assignment deleted successfully!', 'success')
    return redirect(url_for('notes_dashboard'))

@app.route('/notes/<int:note_id>/download')
@login_required
def download_note_file(note_id):
    note = Note.query.get_or_404(note_id)
    if not note.file_path:
        flash('No file attached to this assignment', 'danger')
        return redirect(url_for('notes_dashboard'))
    
    try:
        return send_file(os.path.join(app.static_folder, note.file_path), 
                        download_name=note.file_name,
                        as_attachment=True)
    except Exception as e:
        flash('Error downloading file. Please try again.', 'danger')
        return redirect(url_for('notes_dashboard'))

# ------------------ GAMES ------------------

@app.route("/wordle")
@login_required
def wordle():
    return render_template("wordle/wordle.html", active_page='wordle')

# ------------------ PROFILE IMAGE ------------------

@app.route('/upload_profile_image', methods=['POST'])
@login_required
def upload_profile_image():
    if 'profile_image' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('home'))
    
    file = request.files['profile_image']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('home'))
    
    if file and allowed_file(file.filename, {'png', 'jpg', 'jpeg', 'gif'}):
        # Save the file
        filename = secure_filename(f'profile_{current_user.id}_{file.filename}')
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Update user's profile image in database
        current_user.profile_image = filename
        db.session.commit()
        
        flash('Profile image updated successfully!', 'success')
    else:
        flash('Invalid file type. Please upload an image file.', 'danger')
    
    return redirect(url_for('home'))

# ------------------ MAIN ------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(host='0.0.0.0', port=5000, debug=True)
