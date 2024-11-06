from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def get_db_connection():
    # ฟังก์ชันสำหรับเชื่อมต่อกับฐานข้อมูล SQLite
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

with app.app_context():
    conn = get_db_connection()
    # สร้างตาราง users
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('guest', 'owner')),
                    room TEXT
                )''')
    # สร้างตาราง requests
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
        ('67070163@kmitl.ac.th', '67070163', 'owner', 'A1-101'),
        ('gonggiz@gmail.com', 'gonglnwza007', 'owner', 'A1-102')
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
            # บันทึกข้อมูลผู้ใช้ใหม่ลงในฐานข้อมูล
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

        # ตรวจสอบว่ามีผู้ใช้งานและรหัสผ่านถูกต้องหรือไม่
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['user_email'] = user['email']
            # ตรวจสอบ role ของผู้ใช้ และส่งไปยังหน้าตาม role
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
        owner = conn.execute('SELECT * FROM users WHERE role = "owner" AND room = ?', (f"{room}",)).fetchone()

        if owner:
            # บันทึกข้อมูลการขออนุญาตในฐานข้อมูล
            conn.execute(
                'INSERT INTO requests (guest_id, owner_id, building, floor, room) VALUES (?, ?, ?, ?, ?)',
                (session['user_id'], owner['id'], building, floor, room)
            )
            conn.commit()
            flash('Request sent successfully!')
            return redirect(url_for('sendrequest_status'))
        else:
            flash('Room not found or does not match any owner.')
        conn.close()

    return render_template('sendrequest.html')

@app.route('/sendrequest/status')
def sendrequest_status():
    if 'user_id' not in session or session.get('role') != 'guest':
        return redirect(url_for('login'))

    conn = get_db_connection()
    # ดึงข้อมูลคำขอล่าสุดสำหรับ guest ที่ login อยู่
    request_data = conn.execute(
        '''
        SELECT building, floor, room, status
        FROM requests
        WHERE guest_id = ?
        ORDER BY id DESC
        LIMIT 1
        ''', (session['user_id'],)
    ).fetchone()
    conn.close()
    
    return render_template('sendrequest_status.html', request_data=request_data)

@app.route('/request_status')
def request_status():
    # ดึงข้อมูลมาแสดง
    building = request.args.get('building')
    floor = request.args.get('floor')
    room = request.args.get('room')
    status = request.args.get('status')
    return render_template('request_status.html', building=building, floor=floor, room=room, status=status)

@app.route('/update_request_status/<int:request_id>', methods=['POST'])
def update_request_status(request_id):
    if 'user_id' not in session or session.get('role') != 'owner':
        return redirect(url_for('login'))
    status = request.form.get('status')
    conn = get_db_connection()
    conn.execute('UPDATE requests SET status = ? WHERE id = ?', (status, request_id))
    conn.commit()
    conn.close()
    
    flash('Request status updated successfully!')
    return redirect(url_for('checkrequests'))

@app.route('/checkrequests')
def checkrequests():
    if 'user_id' not in session or session.get('role') != 'owner':
        return redirect(url_for('login'))

    conn = get_db_connection()
    requests = conn.execute('''
        SELECT requests.*, users.email AS guest_email 
        FROM requests 
        JOIN users ON requests.guest_id = users.id 
        WHERE owner_id = ?
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    return render_template('checkrequest.html', requests=requests)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=False)
