# 4Smile Dental Clinic — Full-Stack Website

A complete dental clinic website with Python/Flask backend, SQLite database, JWT admin authentication, and a beautiful responsive frontend.

---

## Features

### Frontend (3-page SPA)
- **Home** — Hero, About, Services preview, Doctor profile, Patient reviews (loaded from DB), Google rating bar
- **Services** — Detailed 8-service cards, 5-step treatment process, 11-question FAQ accordion
- **Appointment** — 4-step multi-step form with validation, Google Maps embed, clinic info sidebar
- **Admin Panel** — Secure login → full dashboard with stats, appointments table, contacts

### Backend (Flask + SQLite)
- JWT authentication for admin
- Full CRUD for appointments (create, list, update status, delete)
- CSV export of appointments
- Contact form submissions
- Patient reviews API
- Dashboard analytics (stats, trends, recent activity)
- Optional email notifications via SMTP

---

## Quick Start

### 1. Install Python (3.10+)

```bash
python3 --version   # ensure 3.10+
```

### 2. Install dependencies

```bash
pip install flask pyjwt
```

### 3. Run the server

```bash
python3 app.py
```

Open: http://localhost:5000

Admin Panel: http://localhost:5000 → click "Admin" in the nav
- Username: `admin`
- Password: `4smile2024`

---

## Project Structure

```
4smile/
├── app.py                  ← Flask backend (all API routes)
├── clinic.db               ← SQLite database (auto-created)
├── requirements.txt
├── README.md
└── static/
    ├── index.html          ← Single-page frontend
    ├── css/
    │   └── style.css       ← Full responsive styles
    └── js/
        └── app.js          ← Frontend logic & API calls
```

---

## Environment Variables (Optional)

Create a `.env` file or export these before running:

```bash
SECRET_KEY=your_super_secret_key_here
ADMIN_USER=admin
ADMIN_PASS=your_secure_password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASS=your_app_password
CLINIC_MAIL=clinic@4smiledental.in
PORT=5000
```

### Gmail SMTP Setup
1. Enable 2-Factor Authentication on your Google account
2. Go to: Google Account → Security → App Passwords
3. Generate an app password for "Mail"
4. Use that 16-character password as `SMTP_PASS`

---

## API Reference

### Public Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/appointments | Book appointment |
| POST | /api/contact | Submit contact message |
| GET  | /api/reviews | Get verified reviews |
| GET  | /api/health | Health check |

### Admin Endpoints (require JWT)
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/auth/login | Admin login |
| GET  | /api/auth/me | Verify token |
| GET  | /api/appointments | List with search/filter/pagination |
| PATCH | /api/appointments/:id | Update appointment status |
| DELETE | /api/appointments/:id | Delete appointment |
| GET  | /api/appointments/export/csv | Download CSV |
| GET  | /api/contacts | List contact messages |
| PATCH | /api/contacts/:id/reply | Mark as replied |
| POST | /api/reviews | Add review |
| GET  | /api/dashboard/stats | Full dashboard analytics |

---

## Deploying to Production

### Option 1: Railway / Render (recommended, free tier)
1. Push to GitHub
2. Connect to Railway.app or Render.com
3. Set environment variables in the dashboard
4. Deploy — done!

### Option 2: VPS (Ubuntu)

```bash
# Install dependencies
pip install flask pyjwt gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Or with systemd service for auto-restart
```

### Option 3: Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install flask pyjwt gunicorn
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

---

## Changing Admin Password

Set the `ADMIN_PASS` environment variable, or edit `app.py`:

```python
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'your_new_password')
```

---

## Database

SQLite database (`clinic.db`) is auto-created on first run with sample data.
For production, consider migrating to PostgreSQL.

---

## Support

**4Smile Dental Clinic**  
Dr. Aman Saifi  
R-28, Jogabai Extension, Batla House, New Delhi – 110025  
📞 +91 73034 56062  
