from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ── Users ────────────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    """Model representing a system user with authentication and role."""
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
    daily_rate = db.Column(db.Float, default=300.0)
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


# ── Prescriptions ─────────────────────────────────────────────────────────────
class Prescription(db.Model):
    __tablename__ = 'prescriptions'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    medicine_id = db.Column(db.Integer, db.ForeignKey('medicines.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    instructions = db.Column(db.String(200))  # e.g., "1-0-1 after food"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    patient = db.relationship('Patient', backref=db.backref('prescriptions', lazy=True, cascade="all, delete-orphan"))
    medicine = db.relationship('Medicine', backref=db.backref('prescriptions', lazy=True))

    def __repr__(self):
        return f'<Prescription {self.id}: Medicine {self.medicine_id} for Patient {self.patient_id}>'


# ── Lab Tests ────────────────────────────────────────────────────────────────
class LabTest(db.Model):
    __tablename__ = 'lab_tests'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    test_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False) # e.g. Blood, Radiology, Urine
    cost = db.Column(db.Float, default=0.0)
    result = db.Column(db.Text)
    status = db.Column(db.String(20), default='Pending') # Pending, Completed
    date = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    patient = db.relationship('Patient', backref=db.backref('lab_tests', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<LabTest {self.test_name} for Patient {self.patient_id}>'


# ── Ambulances ───────────────────────────────────────────────────────────────
class Ambulance(db.Model):
    __tablename__ = 'ambulances'

    id = db.Column(db.Integer, primary_key=True)
    vehicle_number = db.Column(db.String(20), unique=True, nullable=False)
    driver_name = db.Column(db.String(100), nullable=False)
    driver_contact = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Available') # Available, On Duty, Maintenance

    # Relationships
    bookings = db.relationship('AmbulanceBooking', backref='ambulance', lazy=True)

    def __repr__(self):
        return f'<Ambulance {self.vehicle_number}>'


# ── Ambulance Bookings ────────────────────────────────────────────────────────
class AmbulanceBooking(db.Model):
    __tablename__ = 'ambulance_bookings'

    id = db.Column(db.Integer, primary_key=True)
    ambulance_id = db.Column(db.Integer, db.ForeignKey('ambulances.id'), nullable=False)
    patient_name = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(200), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    charges = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Dispatched') # Dispatched, Completed, Cancelled

    def __repr__(self):
        return f'<AmbulanceBooking {self.id}>'


# ── Duty Roster ──────────────────────────────────────────────────────────────
class DutyRoster(db.Model):
    __tablename__ = 'duty_roster'

    id = db.Column(db.Integer, primary_key=True)
    staff_type = db.Column(db.String(20), nullable=False) # doctor, nurse
    staff_id = db.Column(db.Integer, nullable=False) # ID of doctor or nurse
    shift_date = db.Column(db.Date, nullable=False)
    shift_type = db.Column(db.String(20), nullable=False) # Morning, Afternoon, Night
    ward_id = db.Column(db.Integer, db.ForeignKey('wards.id'), nullable=True)
    status = db.Column(db.String(20), default='Scheduled') # Scheduled, Completed, Absent

    # Relationship
    ward = db.relationship('Ward', backref=db.backref('rosters', lazy=True))

    def __repr__(self):
        return f'<DutyRoster {self.staff_type} {self.staff_id} on {self.shift_date}>'


# ── Visitor Logs ─────────────────────────────────────────────────────────────
class VisitorLog(db.Model):
    __tablename__ = 'visitor_logs'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    visitor_name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    relationship = db.Column(db.String(50), nullable=False)
    pass_number = db.Column(db.String(50), unique=True, nullable=False)
    check_in_time = db.Column(db.DateTime, default=datetime.utcnow)
    check_out_time = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='Active') # Active, Checked Out

    # Relationship
    patient = db.relationship('Patient', backref=db.backref('visitor_logs', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<VisitorLog {self.visitor_name} for Patient {self.patient_id}>'


# ── Insurance Claims ─────────────────────────────────────────────────────────
class InsuranceClaim(db.Model):
    __tablename__ = 'insurance_claims'

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    insurance_provider = db.Column(db.String(100), nullable=False)
    policy_number = db.Column(db.String(50), nullable=False)
    claim_amount = db.Column(db.Float, default=0.0)
    approved_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(30), default='Initiated') # Initiated, Pending Approval, Approved, Rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    patient = db.relationship('Patient', backref=db.backref('insurance_claims', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<InsuranceClaim {self.policy_number} for Patient {self.patient_id}>'


# ── Feedbacks ────────────────────────────────────────────────────────────────
class Feedback(db.Model):
    __tablename__ = 'feedbacks'

    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    rating = db.Column(db.Integer, nullable=False) # 1 to 5
    category = db.Column(db.String(50), nullable=False) # e.g. Doctors, Nurses, Cleanliness, Billing, Overall
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Feedback from {self.patient_name} - {self.rating} stars>'

