from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///social.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Create upload folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    likes = db.relationship('Like', backref='user', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True, cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='post', lazy=True, cascade='all, delete-orphan')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('front.html')

@app.route('/dashboard')
@login_required
def dashboard():
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template('dashboard.html', posts=posts, active_page='social')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not email.endswith('@nitdelhi.ac.in'):
            flash('Please use your college email (@nitdelhi.ac.in)', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'danger')
            return redirect(url_for('register'))

        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email.endswith('@nitdelhi.ac.in'):
            flash('Please use your college email (@nitdelhi.ac.in)', 'danger')
            return redirect(url_for('login'))

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html')

@app.route('/create_post', methods=['POST'])
@login_required
def create_post():
    content = request.form.get('content')
    image = request.files.get('image')
    image_path = None

    if image and image.filename:
        # Check if the file is allowed
        if image.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            filename = secure_filename(image.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            image_path = os.path.join('uploads', filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            flash('Invalid file type. Only images are allowed.', 'danger')
            return redirect(url_for('dashboard'))

    post = Post(content=content, image_path=image_path, user_id=current_user.id)
    db.session.add(post)
    db.session.commit()
    flash('Post created successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/like_post/<int:post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    existing_like = Like.query.filter_by(
        user_id=current_user.id,
        post_id=post_id
    ).first()

    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        flash('Post unliked!', 'info')
    else:
        like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(like)
        db.session.commit()
        flash('Post liked!', 'success')

    return redirect(url_for('dashboard'))

@app.route('/add_comment/<int:post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    content = request.form.get('content')
    if content:
        comment = Comment(
            content=content,
            user_id=current_user.id,
            post_id=post_id
        )
        db.session.add(comment)
        db.session.commit()
        flash('Comment added successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.user_id == current_user.id:
        # Delete associated image if it exists
        if post.image_path:
            image_file = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(post.image_path))
            if os.path.exists(image_file):
                os.remove(image_file)
        
        db.session.delete(post)
        db.session.commit()
        flash('Post deleted successfully!', 'success')
    else:
        flash('You can only delete your own posts!', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))

@app.template_filter('has_liked')
def has_liked(post, user_id):
    return any(like.user_id == user_id for like in post.likes)

def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    init_db()  # Initialize database tables
    app.run(host='0.0.0.0', port=5000, debug=True)
