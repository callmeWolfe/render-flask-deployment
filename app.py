from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from datetime import timedelta
import joblib
import pandas as pd

app = Flask(__name__)
app.secret_key = 'simple_secret_key'  # Change this for security

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///protein_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Load the ML model and encoders
try:
    model = joblib.load('protein_model.pkl')
    scaler = joblib.load('scaler.pkl')
    label_encoders = joblib.load('label_encoders.pkl')
except Exception as e:
    print("Error loading model files:", e)
    model, scaler, label_encoders = None, None, None

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class ProteinGoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    goal = db.Column(db.Float, nullable=False)

class ProteinLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    food_item = db.Column(db.String(100), nullable=False)
    protein_content = db.Column(db.Float, nullable=False)

# Create tables
with app.app_context():
    db.create_all()

# ✅ Home & Index Pages
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/index')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

# ✅ Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        first_name = data.get('firstName')
        last_name = data.get('lastName')
        email = data.get('email')
        password = data.get('password')

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(first_name=first_name, last_name=last_name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        return jsonify({'message': 'Registration successful', 'redirect': url_for('index')}), 200

    return render_template('register.html')

# ✅ Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return jsonify({'message': 'Login successful', 'redirect': url_for('index')}), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401

    return render_template('login.html')

# ✅ Logout Route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

# ✅ Tracker Page
@app.route('/tracker')
def tracker():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('tracker.html')

# ✅ API: Get Tracker Data
@app.route('/tracker/data')
def get_tracker_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    today = datetime.utcnow().date()

    goal_entry = ProteinGoal.query.filter_by(user_id=user_id, date=today).first()
    food_entries = ProteinLog.query.filter_by(user_id=user_id, date=today).all()

    goal = goal_entry.goal if goal_entry else 0
    total_protein = sum(entry.protein_content for entry in food_entries)
    remaining_protein = goal - total_protein

    foods = [{'item': entry.food_item, 'protein': entry.protein_content} for entry in food_entries]

    return jsonify({'goal': goal, 'remaining': remaining_protein, 'foods': foods})

# ✅ API: Set Protein Goal
@app.route('/tracker/set-goal', methods=['POST'])
def set_protein_goal():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    goal_value = float(data.get('goal'))
    user_id = session['user_id']
    today = datetime.utcnow().date()

    existing_goal = ProteinGoal.query.filter_by(user_id=user_id, date=today).first()
    
    if existing_goal:
        existing_goal.goal = goal_value
    else:
        new_goal = ProteinGoal(user_id=user_id, date=today, goal=goal_value)
        db.session.add(new_goal)

    db.session.commit()
    return jsonify({'message': 'Goal updated successfully'}), 200


# ✅ API: Add Food Entry (FIXED)
@app.route('/tracker/add-food', methods=['POST'])
def add_food():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        print("Received Data:", data)  # ✅ Debugging print

        food_item = data.get('food_item', '').strip()
        protein_content = data.get('protein_content')

        if not food_item or not isinstance(protein_content, (int, float)) or protein_content <= 0:
            print("Invalid Input:", food_item, protein_content)  # ✅ Debugging print
            return jsonify({'error': 'Invalid food entry'}), 400

        user_id = session['user_id']
        today = datetime.utcnow().date()

        new_entry = ProteinLog(user_id=user_id, food_item=food_item, protein_content=protein_content, date=today)
        db.session.add(new_entry)
        db.session.commit()

        print("Food added successfully!")  # ✅ Debugging print
        return jsonify({'message': 'Food added successfully'}), 200

    except Exception as e:
        print("🚨 ERROR:", str(e))  # ✅ Debugging print
        return jsonify({'error': str(e)}), 500

@app.route('/tracker/weekly-data')
def get_weekly_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user_id = session['user_id']
    today = datetime.utcnow().date()
    
    # Get data for last 7 days
    seven_days_ago = today - timedelta(days=6)
    
    # Get all goals and logs for the week
    goals = ProteinGoal.query.filter(
        ProteinGoal.user_id == user_id,
        ProteinGoal.date >= seven_days_ago,
        ProteinGoal.date <= today
    ).all()
    
    logs = ProteinLog.query.filter(
        ProteinLog.user_id == user_id,
        ProteinLog.date >= seven_days_ago,
        ProteinLog.date <= today
    ).all()
    
    # Process data by day
    daily_data = {}
    for i in range(7):
        current_date = today - timedelta(days=i)
        daily_goal = next((g.goal for g in goals if g.date == current_date), 0)
        daily_protein = sum(l.protein_content for l in logs if l.date == current_date)
        
        daily_data[current_date.strftime('%Y-%m-%d')] = {
            'date': current_date.strftime('%A'),  # Day name
            'goal': daily_goal,
            'achieved': daily_protein,
            'percentage': round((daily_protein / daily_goal * 100) if daily_goal > 0 else 0, 1)
        }
    
    return jsonify(daily_data)
@app.route('/tracker/delete-food', methods=['POST'])
def delete_food():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    food_item = data.get('food_item', '').strip()  # ✅ Trim spaces
    if not food_item:
        return jsonify({'error': 'Invalid request'}), 400
    
    user_id = session['user_id']
    entry = ProteinLog.query.filter_by(user_id=user_id, food_item=food_item).first()
    
    if entry:
        db.session.delete(entry)
        db.session.commit()
        return jsonify({'message': 'Food item deleted successfully'}), 200
    else:
        return jsonify({'error': 'Food item not found'}), 404


# ✅ API: Predict Protein Content
@app.route('/predict', methods=['POST'])
def predict():
    if not all([model, scaler, label_encoders]):
        return jsonify({'error': 'Model files not loaded'}), 500

    data = request.get_json()
    food_item = data.get('food_item')
    grams = data.get('grams')

    try:
        encoded_food_item = label_encoders['Food_Item'].transform([food_item])
        new_sample = pd.DataFrame({'Food_Item': encoded_food_item, 'Grams': [grams]})
        new_sample_scaled = scaler.transform(new_sample)
        protein_prediction = model.predict(new_sample_scaled)

        return jsonify({'protein': round(protein_prediction[0], 2)})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# Run Flask App
if __name__ == '__main__':
    app.run()
