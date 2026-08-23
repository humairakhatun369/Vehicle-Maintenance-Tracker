from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_lab_2' 

DATABASE = 'database.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL)''')
                        
        db.execute('''CREATE TABLE IF NOT EXISTS vehicles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        make TEXT NOT NULL,
                        model TEXT NOT NULL,
                        year INTEGER,
                        mileage INTEGER,
                        FOREIGN KEY(user_id) REFERENCES users(id))''')
                        
        db.execute('''CREATE TABLE IF NOT EXISTS maintenance_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        vehicle_id INTEGER,
                        service_type TEXT NOT NULL,
                        service_date TEXT NOT NULL,
                        cost REAL NOT NULL,
                        FOREIGN KEY(vehicle_id) REFERENCES vehicles(id))''')
        db.commit()

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_pw = generate_password_hash(password)
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed_pw))
            db.commit()
            flash("Registration successful! Please log in.")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists.")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    vehicles = db.execute("SELECT * FROM vehicles WHERE user_id = ?", (session['user_id'],)).fetchall()
    return render_template('dashboard.html', vehicles=vehicles, username=session['username'])

@app.route('/add_vehicle', methods=['POST'])
def add_vehicle():
    if 'user_id' in session:
        make = request.form['make']
        model = request.form['model']
        year = request.form['year']
        mileage = request.form['mileage']
        db = get_db()
        db.execute("INSERT INTO vehicles (user_id, make, model, year, mileage) VALUES (?, ?, ?, ?, ?)",
                   (session['user_id'], make, model, year, mileage))
        db.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete_vehicle/<int:id>', methods=['POST'])
def delete_vehicle(id):
    if 'user_id' in session:
        db = get_db()
        db.execute("DELETE FROM vehicles WHERE id = ? AND user_id = ?", (id, session['user_id']))
        db.commit()
    return redirect(url_for('dashboard'))

@app.route('/vehicle/<int:id>')
def vehicle_details(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    db = get_db()
    vehicle = db.execute("SELECT * FROM vehicles WHERE id = ? AND user_id = ?", (id, session['user_id'])).fetchone()
    if not vehicle:
        return redirect(url_for('dashboard'))
        
    logs = db.execute("SELECT * FROM maintenance_logs WHERE vehicle_id = ? ORDER BY service_date DESC", (id,)).fetchall()
    expense_data = db.execute("SELECT SUM(cost) as total_expense FROM maintenance_logs WHERE vehicle_id = ?", (id,)).fetchone()
    
    total_expense = expense_data['total_expense'] if expense_data['total_expense'] else 0.0

    return render_template('vehicle.html', vehicle=vehicle, logs=logs, total_expense=total_expense)

@app.route('/add_maintenance/<int:vehicle_id>', methods=['POST'])
def add_maintenance(vehicle_id):
    if 'user_id' in session:
        service_type = request.form['service_type']
        service_date = request.form['service_date']
        cost = request.form['cost']
        
        db = get_db()
        # Verify ownership before inserting
        vehicle = db.execute("SELECT * FROM vehicles WHERE id = ? AND user_id = ?", (vehicle_id, session['user_id'])).fetchone()
        if vehicle:
            db.execute("INSERT INTO maintenance_logs (vehicle_id, service_type, service_date, cost) VALUES (?, ?, ?, ?)",
                       (vehicle_id, service_type, service_date, cost))
            db.commit()
    return redirect(url_for('vehicle_details', id=vehicle_id))

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)