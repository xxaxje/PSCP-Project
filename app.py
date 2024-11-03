from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

with app.app_context():
    conn = get_db_connection()
    conn.execute()
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        role = 'guest'

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (email, password, role) VALUES (?, ?, ?)', (email, password, role))
            conn.commit()
            flash('Sign up successful! Please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered. Please use another email.')
        finally:
            conn.close()
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            if user['role'] == 'guest':
                return redirect(url_for('send_request'))
            else:
                return redirect(url_for('check_requests'))
        else:
            flash('Invalid email or password.')
    return render_template('login.html')

@app.route('/send_request')
def send_request():
    if 'user_id' not in session or session.get('role') != 'guest':
        return redirect(url_for('login'))
    return render_template('send_request.html')

@app.route('/check_requests')
def check_requests():
    if 'user_id' not in session or session.get('role') != 'owner':
        return redirect(url_for('login'))
    return "This page is for owners only."

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
