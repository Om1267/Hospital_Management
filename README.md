# Hospital Management System

A **production-ready** Hospital Management System built with **Python Flask**, **SQLAlchemy**, **Bootstrap 5**, and **Chart.js**.

## Features

| Module | Description |
|--------|-------------|
| **Authentication** | Admin, Doctor, Nurse, Receptionist roles with password hashing |
| **Dashboard** | Live stats, Chart.js charts, auto-refresh every 20s |
| **Patients** | Full CRUD, search, pagination, history |
| **Doctors** | CRUD, department filter, card grid |
| **Nurses** | CRUD, shift & ward assignment |
| **Wards** | Bed occupancy tracking, progress bars |
| **Rooms** | Room grid, status filter, type filter |
| **Appointments** | Book/cancel/reschedule, status filter |
| **Medicines** | Inventory, low stock alerts, expiry warnings |
| **Billing** | Hospital & pharmacy bills, GST, print invoice |
| **Reports** | Daily/monthly/revenue/medicine/patient, Excel export |
| **Summary** | Full per-patient summary with billing |

## Tech Stack

- **Backend**: Python 3, Flask, Flask-Login, Flask-WTF, SQLAlchemy
- **Database**: SQLite (zero-config), MySQL-compatible
- **Frontend**: Bootstrap 5, Bootstrap Icons, Chart.js, Vanilla JS
- **Export**: openpyxl (Excel reports)

## Quick Start

```bash
# 1. Enter project folder
cd Hospital_Management

# 2. Activate virtual environment
.\venv\Scripts\activate          # Windows
source venv/bin/activate         # Linux/Mac

# 3. Run (creates DB + seed data on first launch)
python app.py
```

Open browser at **http://127.0.0.1:5000**

**Default credentials:** `admin` / `admin123`

## Folder Structure

```
Hospital_Management/
├── app.py              # Flask app, all routes
├── models.py           # SQLAlchemy models
├── config.py           # Configuration
├── requirements.txt
├── database.db         # SQLite DB (auto-created)
├── templates/          # Jinja2 HTML templates
├── static/
│   ├── css/style.css   # Custom theme
│   └── js/main.js      # AJAX + charts
└── README.md
```

## Default Users (Seeded)

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Admin |

## License

MIT © 2026


## Key Features
- Role-based access control (Admin, Doctor, Nurse)
- Patient registration & discharge management
- Automated billing with PDF export
- Prescription management
- Ward & bed management
- Audit logs for all critical actions

