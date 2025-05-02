from flask import Flask, request, redirect, url_for, render_template, send_from_directory, Blueprint
import os
from flask_login import login_required, current_user
from flask_sqlalchemy import SQLAlchemy

UPLOAD_FOLDER = 'uploads'
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes.db'
db = SQLAlchemy(app)

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

@app.route('/')
def index():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('index.html', files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect('/')
    file = request.files['file']
    if file.filename == '':
        return redirect('/')
    if file:
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(save_path)
        print(f"File saved to: {save_path}")  # Optional: Debug output
    return redirect('/')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

notes = Blueprint('notes', __name__)

@notes.route('/notes')
@login_required
def notes_dashboard():
    user_notes = Note.query.filter_by(user_id=current_user.id).order_by(Note.updated_at.desc()).all()
    return render_template('notes.html', notes=user_notes, active_page='notes')

@notes.route('/notes/new', methods=['GET', 'POST'])
@login_required
def new_note():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            flash('Title and content are required', 'danger')
            return redirect(url_for('notes.new_note'))
        
        note = Note(title=title, content=content, user_id=current_user.id)
        db.session.add(note)
        db.session.commit()
        flash('Note created successfully!', 'success')
        return redirect(url_for('notes.notes_dashboard'))
    
    return render_template('new_note.html', active_page='notes')

@notes.route('/notes/<int:note_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id:
        flash('You do not have permission to edit this note', 'danger')
        return redirect(url_for('notes.notes_dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            flash('Title and content are required', 'danger')
            return redirect(url_for('notes.edit_note', note_id=note_id))
        
        note.title = title
        note.content = content
        db.session.commit()
        flash('Note updated successfully!', 'success')
        return redirect(url_for('notes.notes_dashboard'))
    
    return render_template('edit_note.html', note=note, active_page='notes')

@notes.route('/notes/<int:note_id>/delete', methods=['POST'])
@login_required
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id:
        flash('You do not have permission to delete this note', 'danger')
        return redirect(url_for('notes.notes_dashboard'))
    
    db.session.delete(note)
    db.session.commit()
    flash('Note deleted successfully!', 'success')
    return redirect(url_for('notes.notes_dashboard'))

app.register_blueprint(notes)

if __name__ == '__main__':
    app.run(debug=True)