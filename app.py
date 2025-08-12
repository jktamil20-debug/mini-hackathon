from flask import Flask, render_template, request, redirect, url_for, flash, session
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['clinic_db']
users = db['users']
records = db['records']
appointments = db['appointments']

# Home route
@app.route('/')
def home():
    return redirect(url_for('login'))

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['role'] = user['role']
            if user['role'] == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        name = request.form['name']
        if users.find_one({'email': email}):
            flash('Email already exists')
        else:
            hashed_password = generate_password_hash(password)
            users.insert_one({
                'email': email,
                'password': hashed_password,
                'role': role,
                'name': name
            })
            flash('Registration successful. Please login.')
            return redirect(url_for('login'))
    return render_template('register.html')

# Doctor Dashboard
@app.route('/doctor_dashboard')
def doctor_dashboard():
    if 'user_id' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))
    patients = users.find({'role': 'patient'})
    return render_template('doctor_dashboard.html', patients=patients)

# Patient Dashboard
@app.route('/patient_dashboard')
def patient_dashboard():
    if 'user_id' not in session or session['role'] != 'patient':
        return redirect(url_for('login'))
    patient_id = session['user_id']
    patient_records = records.find({'patient_id': patient_id})
    patient_appointments = appointments.find({'patient_id': patient_id})
    return render_template('patient_dashboard.html', records=patient_records, appointments=patient_appointments)

# Patient Records (Doctor View)
@app.route('/patient_records/<patient_id>', methods=['GET', 'POST'])
def patient_records(patient_id):
    if 'user_id' not in session or session['role'] != 'doctor':
        return redirect(url_for('login'))
    patient = users.find_one({'_id': ObjectId(patient_id)})
    if request.method == 'POST':
        diagnosis = request.form['diagnosis']
        treatment = request.form['treatment']
        records.insert_one({
            'patient_id': patient_id,
            'diagnosis': diagnosis,
            'treatment': treatment,
            'date': datetime.datetime.now()
        })
        flash('Record added successfully')
    patient_records = records.find({'patient_id': patient_id})
    return render_template('patient_records.html', patient=patient, records=patient_records)

# Appointments
@app.route('/appointments', methods=['GET', 'POST'])
def appointments_route():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        patient_id = session['user_id'] if session['role'] == 'patient' else request.form['patient_id']
        date = request.form['date']
        time = request.form['time']
        doctor_id = request.form['doctor_id'] if session['role'] == 'patient' else session['user_id']
        appointments.insert_one({
            'patient_id': patient_id,
            'doctor_id': doctor_id,
            'date': date,
            'time': time,
            'status': 'scheduled'
        })
        flash('Appointment booked successfully')
    doctors = users.find({'role': 'doctor'})
    user_appointments = appointments.find({
        '$or': [
            {'patient_id': session['user_id']},
            {'doctor_id': session['user_id']}
        ]
    })
    return render_template('appointments.html', doctors=doctors, appointments=user_appointments)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)