"""
4Smile Dental Clinic - Full Stack Backend
Flask + SQLite + JWT Authentication
"""

import os
import sqlite3
import hashlib
import hmac
import json
import csv
import io
import re
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_from_directory, g, make_response

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

app = Flask(__name__)

# ─── CONFIG ──────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY', '4smile_dental_super_secret_2024_xK9mP')
DB_PATH    = os.path.join(os.path.dirname(__file__), 'clinic.db')
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', '4smile2024')

# Email config (optional – set these env vars to enable real email)
SMTP_HOST  = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT  = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER  = os.environ.get('SMTP_USER', '')
SMTP_PASS  = os.environ.get('SMTP_PASS', '')
CLINIC_MAIL= os.environ.get('CLINIC_MAIL', 'clinic@4smiledental.in')

# ─── DATABASE ────────────────────────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db

@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop('db', None)
    if db:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.executescript("""
        CREATE TABLE IF NOT EXISTS appointments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name   TEXT NOT NULL,
            age         INTEGER,
            gender      TEXT,
            phone       TEXT NOT NULL,
            whatsapp    TEXT,
            email       TEXT,
            address     TEXT,
            city        TEXT DEFAULT 'New Delhi',
            state       TEXT DEFAULT 'Delhi',
            pin_code    TEXT,
            pref_date   TEXT NOT NULL,
            pref_time   TEXT NOT NULL,
            reason      TEXT NOT NULL,
            conditions  TEXT,
            medications TEXT,
            allergies   TEXT,
            prev_dental TEXT,
            message     TEXT,
            status      TEXT DEFAULT 'pending'
                        CHECK(status IN ('pending','confirmed','completed','cancelled')),
            created_at  TEXT DEFAULT (datetime('now','localtime')),
            updated_at  TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            email      TEXT,
            phone      TEXT,
            subject    TEXT,
            message    TEXT NOT NULL,
            replied    INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            patient    TEXT NOT NULL,
            rating     INTEGER DEFAULT 5,
            treatment  TEXT,
            comment    TEXT NOT NULL,
            verified   INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS analytics (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            event      TEXT NOT NULL,
            page       TEXT,
            meta       TEXT,
            ip         TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        """)

        # Seed sample data
        count = db.execute('SELECT COUNT(*) FROM appointments').fetchone()[0]
        if count == 0:
            samples = [
                ('Rahul Sharma',    34,'Male',  '+91 98765 43210','','rahul@email.com','Sector 12','New Delhi','Delhi','110025','2024-06-20','11:00 AM - 12:00 PM','Consultation',  'None','None','None','','','confirmed'),
                ('Priya Gupta',     28,'Female','+91 87654 32109','','priya@email.com','Batla House','New Delhi','Delhi','110025','2024-06-21','3:00 PM - 4:00 PM', 'Root Canal',    'None','None','None','','','pending'),
                ('Mohammed Alam',   45,'Male',  '+91 76543 21098','','','Okhla','New Delhi','Delhi','110020','2024-06-22','10:00 AM - 11:00 AM','Teeth Cleaning','Diabetes','Metformin','None','','','confirmed'),
                ('Anjali Verma',    22,'Female','+91 65432 10987','','anjali@mail.com','Jamia Nagar','New Delhi','Delhi','110025','2024-06-23','4:00 PM - 5:00 PM', 'Dental Filling','None','None','None','Previous filling 2020','','completed'),
                ('Suresh Kumar',    55,'Male',  '+91 54321 09876','','','Sarita Vihar','New Delhi','Delhi','110076','2024-06-24','2:00 PM - 3:00 PM',  'Tooth Extraction','BP','Amlodipine','Penicillin','','','pending'),
            ]
            db.executemany("""INSERT INTO appointments
                (full_name,age,gender,phone,whatsapp,email,address,city,state,pin_code,
                 pref_date,pref_time,reason,conditions,medications,allergies,prev_dental,message,status)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", samples)

            db.executemany("INSERT INTO reviews (patient,rating,treatment,comment,verified) VALUES (?,?,?,?,?)", [
                ('Rahul S.',    5,'Root Canal',   'Dr. Saifi is exceptional — explained every step. Virtually painless!', 1),
                ('Priya G.',    5,'Teeth Cleaning','Best dental clinic in Batla House. Very affordable and professional.', 1),
                ('Mohammed A.', 5,'Tooth Extraction','Very nervous but Dr. Saifi was so gentle. No pain at all!', 1),
                ('Anjali V.',   5,'Dental Filling','Quick and painless. Staff very friendly. Highly recommend!', 1),
                ('Suresh K.',   5,'Consultation',  'Very thorough consultation. Dr. Saifi took time to explain everything.', 1),
            ])
            db.commit()

        count_rev = db.execute('SELECT COUNT(*) FROM reviews').fetchone()[0]
        if count_rev == 0:
            db.commit()

init_db()

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def make_token(payload):
    if JWT_AVAILABLE:
        payload['exp'] = datetime.utcnow() + timedelta(hours=8)
        return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    # fallback simple token
    import base64
    data = json.dumps({**payload, 'exp': (datetime.utcnow() + timedelta(hours=8)).isoformat()})
    return base64.b64encode(data.encode()).decode()

def verify_token(token):
    if not token:
        return None
    try:
        if JWT_AVAILABLE:
            return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        import base64
        data = json.loads(base64.b64decode(token.encode()).decode())
        if datetime.fromisoformat(data['exp']) < datetime.utcnow():
            return None
        return data
    except Exception:
        return None

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            token = request.cookies.get('admin_token', '')
        payload = verify_token(token)
        if not payload or payload.get('role') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

def row_to_dict(row):
    return dict(row) if row else None

def rows_to_list(rows):
    return [dict(r) for r in rows]

def send_email(to, subject, html_body):
    """Send email via SMTP — silently skips if not configured."""
    if not SMTP_USER or not SMTP_PASS:
        print(f"[Email skipped — SMTP not configured] To: {to} | Subject: {subject}")
        return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = SMTP_USER
        msg['To']      = to
        msg.attach(MIMEText(html_body, 'html'))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[Email error] {e}")
        return False

def track(event, page=None, meta=None):
    try:
        db = get_db()
        db.execute("INSERT INTO analytics (event,page,meta,ip) VALUES (?,?,?,?)",
                   (event, page, json.dumps(meta) if meta else None, request.remote_addr))
        db.commit()
    except Exception:
        pass

def validate_phone(phone):
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
    return len(cleaned) >= 10

def validate_email(email):
    if not email:
        return True  # optional
    return re.match(r'^[^@]+@[^@]+\.[^@]+$', email) is not None

# ─── STATIC / FRONTEND ───────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    if path.startswith('api/'):
        return jsonify({'error': 'Not found'}), 404
    try:
        return send_from_directory('.', path)
    except Exception:
        return send_from_directory('.', 'index.html')

# ─── AUTH ────────────────────────────────────────────────────────────────────
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    if username == ADMIN_USER and password == ADMIN_PASS:
        token = make_token({'username': username, 'role': 'admin'})
        track('admin_login')
        resp = jsonify({'token': token, 'username': username, 'role': 'admin'})
        resp.set_cookie('admin_token', token, httponly=True, max_age=28800, samesite='Lax')
        return resp
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    resp = jsonify({'message': 'Logged out'})
    resp.delete_cookie('admin_token')
    return resp

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def me():
    return jsonify({'username': ADMIN_USER, 'role': 'admin'})

# ─── APPOINTMENTS ─────────────────────────────────────────────────────────────
@app.route('/api/appointments', methods=['POST'])
def create_appointment():
    data = request.get_json() or {}

    # Validation
    required = ['full_name', 'phone', 'pref_date', 'pref_time', 'reason']
    missing  = [f for f in required if not data.get(f, '').strip()]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    if not validate_phone(data['phone']):
        return jsonify({'error': 'Invalid phone number'}), 400

    if data.get('email') and not validate_email(data.get('email')):
        return jsonify({'error': 'Invalid email address'}), 400

    # Check duplicate (same phone + date)
    db = get_db()
    existing = db.execute(
        "SELECT id FROM appointments WHERE phone=? AND pref_date=? AND status != 'cancelled'",
        (data['phone'], data['pref_date'])
    ).fetchone()
    if existing:
        return jsonify({'error': 'An appointment already exists for this phone number on that date.'}), 409

    db.execute("""
        INSERT INTO appointments
          (full_name,age,gender,phone,whatsapp,email,address,city,state,pin_code,
           pref_date,pref_time,reason,conditions,medications,allergies,prev_dental,message)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data['full_name'].strip(),
        data.get('age') or None,
        data.get('gender', ''),
        data['phone'].strip(),
        data.get('whatsapp', ''),
        data.get('email', ''),
        data.get('address', ''),
        data.get('city', 'New Delhi'),
        data.get('state', 'Delhi'),
        data.get('pin_code', ''),
        data['pref_date'],
        data['pref_time'],
        data['reason'],
        data.get('conditions', ''),
        data.get('medications', ''),
        data.get('allergies', ''),
        data.get('prev_dental', ''),
        data.get('message', ''),
    ))
    db.commit()
    appt_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    track('appointment_booked', meta={'id': appt_id, 'reason': data['reason']})

    # Send confirmation email to patient
    if data.get('email'):
        send_email(
            data['email'],
            f"Appointment Confirmed – 4Smile Dental Clinic (#{appt_id})",
            f"""
            <h2>Thank you, {data['full_name']}!</h2>
            <p>Your appointment request has been received.</p>
            <table>
              <tr><td><b>Date:</b></td><td>{data['pref_date']}</td></tr>
              <tr><td><b>Time:</b></td><td>{data['pref_time']}</td></tr>
              <tr><td><b>Reason:</b></td><td>{data['reason']}</td></tr>
            </table>
            <p>We will call you to confirm. For urgent queries: <b>+91 73034 56062</b></p>
            <p>— 4Smile Dental Clinic, Batla House, New Delhi</p>
            """
        )
    # Notify clinic
    send_email(
        CLINIC_MAIL,
        f"New Appointment #{appt_id} – {data['full_name']} ({data['reason']})",
        f"<b>Patient:</b> {data['full_name']}<br><b>Phone:</b> {data['phone']}<br>"
        f"<b>Date:</b> {data['pref_date']} {data['pref_time']}<br><b>Reason:</b> {data['reason']}"
    )

    return jsonify({'message': 'Appointment booked successfully', 'id': appt_id}), 201

@app.route('/api/appointments', methods=['GET'])
@require_auth
def get_appointments():
    db     = get_db()
    status = request.args.get('status')
    search = request.args.get('search', '').strip()
    date   = request.args.get('date')
    page   = max(1, int(request.args.get('page', 1)))
    limit  = int(request.args.get('limit', 50))
    offset = (page - 1) * limit

    query  = "SELECT * FROM appointments WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"; params.append(status)
    if search:
        query += " AND (full_name LIKE ? OR phone LIKE ? OR reason LIKE ? OR email LIKE ?)"
        s = f'%{search}%'; params.extend([s, s, s, s])
    if date:
        query += " AND pref_date=?"; params.append(date)

    total = db.execute(query.replace('SELECT *', 'SELECT COUNT(*)'), params).fetchone()[0]
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows  = db.execute(query, params).fetchall()

    return jsonify({
        'appointments': rows_to_list(rows),
        'total': total,
        'page': page,
        'pages': (total + limit - 1) // limit
    })

@app.route('/api/appointments/<int:appt_id>', methods=['GET'])
@require_auth
def get_appointment(appt_id):
    db   = get_db()
    row  = db.execute("SELECT * FROM appointments WHERE id=?", (appt_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(row_to_dict(row))

@app.route('/api/appointments/<int:appt_id>', methods=['PATCH'])
@require_auth
def update_appointment(appt_id):
    data    = request.get_json() or {}
    db      = get_db()
    allowed = {'status', 'pref_date', 'pref_time', 'reason', 'message'}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({'error': 'Nothing to update'}), 400
    if 'status' in updates and updates['status'] not in ('pending','confirmed','completed','cancelled'):
        return jsonify({'error': 'Invalid status'}), 400

    sets   = ', '.join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), appt_id]
    db.execute(f"UPDATE appointments SET {sets}, updated_at=? WHERE id=?", values)
    db.commit()
    track('appointment_updated', meta={'id': appt_id, **updates})
    return jsonify({'message': 'Updated successfully'})

@app.route('/api/appointments/<int:appt_id>', methods=['DELETE'])
@require_auth
def delete_appointment(appt_id):
    db = get_db()
    db.execute("DELETE FROM appointments WHERE id=?", (appt_id,))
    db.commit()
    return jsonify({'message': 'Deleted'})

@app.route('/api/appointments/export/csv', methods=['GET'])
@require_auth
def export_csv():
    db   = get_db()
    rows = db.execute("SELECT * FROM appointments ORDER BY created_at DESC").fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID','Name','Age','Gender','Phone','WhatsApp','Email','Address','City',
                     'State','PIN','Date','Time','Reason','Conditions','Medications',
                     'Allergies','Prev Dental','Message','Status','Created At'])
    for r in rows:
        d = dict(r)
        writer.writerow([d.get(k,'') for k in [
            'id','full_name','age','gender','phone','whatsapp','email','address','city',
            'state','pin_code','pref_date','pref_time','reason','conditions','medications',
            'allergies','prev_dental','message','status','created_at']])
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = 'attachment; filename=4smile_appointments.csv'
    return response

# ─── CONTACTS ─────────────────────────────────────────────────────────────────
@app.route('/api/contact', methods=['POST'])
def submit_contact():
    data = request.get_json() or {}
    if not data.get('name') or not data.get('message'):
        return jsonify({'error': 'Name and message are required'}), 400
    db = get_db()
    db.execute("INSERT INTO contacts (name,email,phone,subject,message) VALUES (?,?,?,?,?)",
               (data['name'], data.get('email',''), data.get('phone',''),
                data.get('subject','General Enquiry'), data['message']))
    db.commit()
    track('contact_submitted')
    return jsonify({'message': 'Message sent successfully'}), 201

@app.route('/api/contacts', methods=['GET'])
@require_auth
def get_contacts():
    db   = get_db()
    rows = db.execute("SELECT * FROM contacts ORDER BY created_at DESC").fetchall()
    return jsonify({'contacts': rows_to_list(rows)})

@app.route('/api/contacts/<int:cid>/reply', methods=['PATCH'])
@require_auth
def mark_replied(cid):
    db = get_db()
    db.execute("UPDATE contacts SET replied=1 WHERE id=?", (cid,))
    db.commit()
    return jsonify({'message': 'Marked as replied'})

# ─── REVIEWS ─────────────────────────────────────────────────────────────────
@app.route('/api/reviews', methods=['GET'])
def get_reviews():
    db   = get_db()
    rows = db.execute("SELECT * FROM reviews WHERE verified=1 ORDER BY created_at DESC").fetchall()
    return jsonify({'reviews': rows_to_list(rows)})

@app.route('/api/reviews', methods=['POST'])
@require_auth
def add_review():
    data = request.get_json() or {}
    db   = get_db()
    db.execute("INSERT INTO reviews (patient,rating,treatment,comment,verified) VALUES (?,?,?,?,?)",
               (data.get('patient','Anonymous'), data.get('rating', 5),
                data.get('treatment',''), data.get('comment',''), data.get('verified', 0)))
    db.commit()
    return jsonify({'message': 'Review added'}), 201

# ─── DASHBOARD ANALYTICS ─────────────────────────────────────────────────────
@app.route('/api/dashboard/stats', methods=['GET'])
@require_auth
def dashboard_stats():
    db = get_db()

    total      = db.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
    pending    = db.execute("SELECT COUNT(*) FROM appointments WHERE status='pending'").fetchone()[0]
    confirmed  = db.execute("SELECT COUNT(*) FROM appointments WHERE status='confirmed'").fetchone()[0]
    completed  = db.execute("SELECT COUNT(*) FROM appointments WHERE status='completed'").fetchone()[0]
    cancelled  = db.execute("SELECT COUNT(*) FROM appointments WHERE status='cancelled'").fetchone()[0]
    contacts   = db.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
    new_contact= db.execute("SELECT COUNT(*) FROM contacts WHERE replied=0").fetchone()[0]
    reviews    = db.execute("SELECT COUNT(*) FROM reviews WHERE verified=1").fetchone()[0]
    avg_rating = db.execute("SELECT AVG(rating) FROM reviews WHERE verified=1").fetchone()[0] or 5.0

    today = datetime.now().strftime('%Y-%m-%d')
    today_appts = db.execute(
        "SELECT COUNT(*) FROM appointments WHERE pref_date=?", (today,)).fetchone()[0]

    # Appointments by reason
    by_reason = db.execute(
        "SELECT reason, COUNT(*) as cnt FROM appointments GROUP BY reason ORDER BY cnt DESC LIMIT 8"
    ).fetchall()

    # Last 7 days trend
    trend = db.execute("""
        SELECT DATE(created_at) as day, COUNT(*) as cnt
        FROM appointments
        WHERE created_at >= DATE('now','-7 days')
        GROUP BY day ORDER BY day
    """).fetchall()

    # Recent appointments
    recent = db.execute(
        "SELECT id,full_name,phone,pref_date,pref_time,reason,status FROM appointments ORDER BY created_at DESC LIMIT 5"
    ).fetchall()

    return jsonify({
        'total': total, 'pending': pending, 'confirmed': confirmed,
        'completed': completed, 'cancelled': cancelled,
        'contacts': contacts, 'new_contacts': new_contact,
        'reviews': reviews, 'avg_rating': round(avg_rating, 1),
        'today': today_appts,
        'by_reason': rows_to_list(by_reason),
        'trend': rows_to_list(trend),
        'recent': rows_to_list(recent),
    })

# ─── HEALTH CHECK ─────────────────────────────────────────────────────────────
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat(), 'clinic': '4Smile Dental'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n{'='*60}")
    print(f"  4Smile Dental Clinic — Backend Server")
    print(f"  Running at: http://localhost:{port}")
    print(f"  Admin:      http://localhost:{port}/admin")
    print(f"  API Docs:   http://localhost:{port}/api/health")
    print(f"{'='*60}\n")
    app.run(host='0.0.0.0', port=port, debug=False)
