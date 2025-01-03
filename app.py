from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os
import json
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Setup Flask-Login
app.config['SECRET_KEY'] = 'your-secret-key'  # Required for session management
login_manager = LoginManager()
login_manager.init_app(app)

# Set up the directory to save files
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Define the allowed file extensions for videos and images
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mkv', 'avi'}
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png'}

# Initialize a simple data structure for storing users and their files
def init_data():
    if not os.path.exists('data.json'):
        with open('data.json', 'w') as f:
            json.dump({}, f)  # Initialize empty data structure

# Load the data from the file
def load_data():
    with open('data.json', 'r') as f:
        return json.load(f)

# Save the data back to the file
def save_data(data):
    with open('data.json', 'w') as f:
        json.dump(data, f)

init_data()

# User Class for Flask-Login
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# Load user from the session
@login_manager.user_loader
def load_user(user_id):
    data = load_data()
    if user_id in data:
        return User(user_id)
    return None

# Utility to check allowed file extensions
def allowed_file(filename, file_type):
    if file_type == 'video':
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS
    elif file_type == 'image':
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
    return False

# Home page (Display uploaded videos and images)
@app.route('/')
def home():
    data = load_data()
    
    # Separate videos and images into different categories
    videos = []
    images = []
    
    for username, user_data in data.items():
        for video in user_data.get('videos', []):
            videos.append({'type': 'video', 'filename': video, 'username': username})
        for image in user_data.get('images', []):
            images.append({'type': 'image', 'filename': image, 'username': username})

    # Pass videos and images separately to the template
    return render_template('index.html', videos=videos, images=images, logged_in=current_user.is_authenticated, username=current_user.id if current_user.is_authenticated else None)


# Channel page
@app.route('/channel/<username>')
def channel(username):
    # Check if the user exists in the data
    data = load_data()
    
    if username not in data:
        # If the user doesn't exist, show a 404 error or redirect
        return render_template('404.html'), 404

    user_data = data[username]
    
    # Pass videos and images for the user to the template
    return render_template('channel.html', 
                           username=username, 
                           logged_in=current_user.is_authenticated,
                           videos=user_data.get('videos', []),
                           images=user_data.get('images', []))


# Upload page
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        username = current_user.id
        file = request.files['file']
        file_type = request.form['file_type']
        
        if file and allowed_file(file.filename, file_type):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            data = load_data()

            # If the user doesn't exist, create a new entry
            if username not in data:
                data[username] = {"videos": [], "images": [], "likes": {}}

            # Save the file to the respective list (videos/images)
            if file_type == 'video':
                data[username]['videos'].append(filename)
            elif file_type == 'image':
                data[username]['images'].append(filename)

            save_data(data)

            return redirect(url_for('channel', username=username))
    
    return render_template('upload.html')

# Like functionality
@app.route('/like/<username>/<product_type>/<filename>', methods=['POST'])
@login_required
def like(username, product_type, filename):
    data = load_data()

    # Increment likes count for the product
    if username in data:
        if product_type == 'video' and filename in data[username]['videos']:
            if filename not in data[username]['likes']:
                data[username]['likes'][filename] = 0
            data[username]['likes'][filename] += 1
        save_data(data)

    return redirect(url_for('home'))

# Registration page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = generate_password_hash(password)

        data = load_data()

        if username in data:
            flash('Username already taken', 'danger')
            return redirect(url_for('register'))

        # Save user data
        data[username] = {"password": password_hash, "videos": [], "images": [], "likes": {}}
        save_data(data)

        user = User(username)
        login_user(user)

        return redirect(url_for('channel', username=username))

    return render_template('register.html')

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        data = load_data()

        if username in data and check_password_hash(data[username]['password'], password):
            user = User(username)
            login_user(user)
            return redirect(url_for('channel', username=username))
        else:
            flash('Invalid credentials', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
