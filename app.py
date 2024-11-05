from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

with app.app_context():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('guest', 'owner')),
                    room TEXT
                )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guest_id INTEGER NOT NULL,
                    owner_id INTEGER NOT NULL,
                    building TEXT,
                    floor INTEGER,
                    room TEXT,
                    status TEXT DEFAULT 'pending',
                    FOREIGN KEY(guest_id) REFERENCES users(id),
                    FOREIGN KEY(owner_id) REFERENCES users(id)
                )''')
    predefined_owners = [
        ('67070163@kmitl.ac.th', '67070163', 'owner', 'A1-201'),
        ('gonggiz@gmail.com', 'gonglnwza007', 'owner', 'A2-102')
    ]

    for email, password, role, room in predefined_owners:
        try:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            conn.execute('INSERT INTO users (email, password, role, room) VALUES (?, ?, ?, ?)', 
                         (email, hashed_password, role, room))
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
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
            if user['role'] == 'owner':
                return redirect(url_for('checkrequests'))
            else:
                return redirect(url_for('sendrequest'))
        else:
            flash('Invalid email or password.')
    return render_template('login.html')

@app.route('/sendrequest', methods=['GET', 'POST'])
def sendrequest():
    if 'user_id' not in session or session.get('role') != 'guest':
        return redirect(url_for('login'))

    if request.method == 'POST':
        building = request.form['building']
        floor = request.form['floor']
        room = request.form['room']
        conn = get_db_connection()
        owner = conn.execute('SELECT * FROM users WHERE role = "owner" AND room = ?', (f"{building}-{room}",)).fetchone()

        if owner:
            conn.execute(
                'INSERT INTO requests (guest_id, owner_id, building, floor, room) VALUES (?, ?, ?, ?, ?)',
                (session['user_id'], owner['id'], building, floor, room)
            )
            conn.commit()
            flash('Request sent successfully!')
            return redirect(url_for('checkrequests', email=owner['email']))
        else:
            flash('Room not found or does not match any owner.')
        
        conn.close()
    return render_template('sendrequest.html')

@app.route('/checkrequests')
def checkrequests():
    if 'user_id' not in session or session.get('role') != 'owner':
        return redirect(url_for('login')) 
    email = request.args.get('email')
    conn = get_db_connection()
    requests = conn.execute('SELECT * FROM requests WHERE owner_id = ?', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('checkrequest.html', email=email, requests=requests)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
