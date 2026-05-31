from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ── Users ────────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='receptionist')
    # Roles: admin, doctor, nurse, receptionist
    full_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active_user = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


# ── Doctors ──────────────────────────────────────────────────────────────────
class Doctor(db.Model):
    __tablename__ = 'doctors'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    qualification = db.Column(db.String(200), nullable=False)
    experience = db.Column(db.Integer, default=0)
    contact = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    availability = db.Column(db.String(50), default='Available')
    salary = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    patients = db.relationship('Patient', backref='doctor', lazy=True)
    appointments = db.relationship('Appointment', backref='doctor', lazy=True)

    def __repr__(self):
        return f'<Doctor {self.name}>'


# ── Nurses ───────────────────────────────────────────────────────────────────
class Nurse(db.Model):
    __tablename__ = 'nurses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    shift = db.Column(db.String(20), nullable=False, default='Morning')
    # Shifts: Morning, Afternoon, Night
    contact = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    ward_id = db.Column(db.Integer, db.ForeignKey('wards.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Nurse {self.name}>'


# ── Wards ────────────────────────────────────────────────────────────────────
class Ward(db.Model):
    __tablename__ = 'wards'

    id = db.Column(db.Integer, primary_key=True)
    ward_number = db.Column(db.String(20), unique=True, nullable=False)
    ward_type = db.Column(db.String(50), nullable=False)
    # Types: General, Pediatric, Maternity, Surgical, ICU
    capacity = db.Column(db.Integer, nullable=False, default=10)
    available_beds = db.Column(db.Integer, nullable=False, default=10)
    occupied_beds = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    patients = db.relationship('Patient', backref='ward', lazy=True)
    nurses = db.relationship('Nurse', backref='ward', lazy=True)

    def __repr__(self):
        return f'<Ward {self.ward_number}>'


# ── Rooms ────────────────────────────────────────────────────────────────────
class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(20), unique=True, nullable=False)
    room_type = db.Column(db.String(30), nullable=False, default='General')
    # Types: General, Semi-Private, Private, ICU
    floor = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default='Available')
    # Status: Available, Occupied, Maintenance
    daily_rate = db.Column(db.Float, default=500.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    patients = db.relationship('Patient', backref='room', lazy=True)

    def __repr__(self):
        return f'<Room {self.room_number}>'


# ── Patients ─────────────────────────────────────────────────────────────────
class Patient(db.Model):
    __tablename__ = 'patients'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    blood_group = db.Column(db.String(5))
    mobile = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    emergency_contact = db.Column(db.String(20))
    admission_date = db.Column(db.DateTime, default=datetime.utcnow)
    discharge_date = db.Column(db.DateTime, nullable=True)
    disease = db.Column(db.String(200))
    status = db.Column(db.String(20), default='Admitted')
    # Status: Admitted, Discharged, Under Treatment

    # Foreign Keys
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)
    ward_id = db.Column(db.Integer, db.ForeignKey('wards.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    appointments = db.relationship('Appointment', backref='patient', lazy=True)
    bills = db.relationship('Bill', backref='patient', lazy=True)

    def __repr__(self):
        return f'<Patient {self.name}>'


# ── Appointments ─────────────────────────────────────────────────────────────
class Appointment(db.Model):
    __tablename__ = 'appointments'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), default='Scheduled')
    # Status: Scheduled, Completed, Cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Appointment {self.id}>'


# ── Medicines ────────────────────────────────────────────────────────────────
class Medicine(db.Model):
    __tablename__ = 'medicines'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    batch_number = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    expiry_date = db.Column(db.Date, nullable=False)
    price = db.Column(db.Float, nullable=False, default=0.0)
    manufacturer = db.Column(db.String(100))
    category = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Medicine {self.name}>'


# ── Bills ────────────────────────────────────────────────────────────────────
class Bill(db.Model):
    __tablename__ = 'bills'

    id = db.Column(db.Integer, primary_key=True)
    bill_number = db.Column(db.String(20), unique=True, nullable=False)
    bill_type = db.Column(db.String(20), nullable=False, default='Hospital')
    # Types: Hospital, Pharmacy
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    items_json = db.Column(db.Text)  # JSON string of line items
    subtotal = db.Column(db.Float, default=0.0)
    gst = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.String(20), default='Pending')
    # Status: Pending, Paid, Partial
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Bill {self.bill_number}>'
