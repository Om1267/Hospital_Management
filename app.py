import os
import sys
# Force UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import json
import datetime
from datetime import timezone
from functools import wraps

from flask import (
    Flask, render_template, redirect, url_for,
    flash, request, jsonify, make_response
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, SelectField,
    IntegerField, DateField, FloatField, TextAreaField
)
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, User, Doctor, Nurse, Ward, Room, Patient, Appointment, Medicine, Bill, Prescription
from config import Config

from flask_wtf.csrf import CSRFProtect

# ─── App Setup ───────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
csrf = CSRFProtect(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ─── Role Decorator ──────────────────────────────────────────────────────────
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in roles:
                flash('Access denied.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ─── Forms ───────────────────────────────────────────────────────────────────
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(4, 25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(6)])
    role = SelectField('Role', choices=[
        ('admin', 'Admin'), ('doctor', 'Doctor'),
        ('nurse', 'Nurse'), ('receptionist', 'Receptionist')
    ])
    full_name = StringField('Full Name', validators=[DataRequired()])
    submit = SubmitField('Register')


# ─── Auth Routes ─────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(request.args.get('next') or url_for('dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already taken.', 'danger')
        elif User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'danger')
        else:
            u = User(
                username=form.username.data,
                email=form.email.data,
                full_name=form.full_name.data,
                role=form.role.data
            )
            u.set_password(form.password.data)
            db.session.add(u)
            db.session.commit()
            flash('Account created. Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)


# ─── Dashboard ───────────────────────────────────────────────────────────────
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    stats = {
        'total_patients': Patient.query.count(),
        'admitted_patients': Patient.query.filter_by(status='Admitted').count(),
        'discharged_patients': Patient.query.filter_by(status='Discharged').count(),
        'total_doctors': Doctor.query.count(),
        'total_nurses': Nurse.query.count(),
        'available_rooms': Room.query.filter_by(status='Available').count(),
        'available_beds': db.session.query(db.func.sum(Ward.available_beds)).scalar() or 0,
        'revenue': db.session.query(db.func.sum(Bill.total)).scalar() or 0.0,
    }
    recent_appointments = (
        Appointment.query
        .order_by(Appointment.created_at.desc())
        .limit(10).all()
    )
    return render_template('dashboard.html', stats=stats, recent_appointments=recent_appointments)


# ─── Patients ────────────────────────────────────────────────────────────────
@app.route('/patients')
@login_required
def patients():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '')
    query = Patient.query
    if q:
        query = query.filter(
            (Patient.name.ilike(f'%{q}%')) |
            (Patient.disease.ilike(f'%{q}%')) |
            (Patient.mobile.ilike(f'%{q}%'))
        )
    pag = query.order_by(Patient.id.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('patients.html', patients=pag, search=q)


@app.route('/patients/add', methods=['GET', 'POST'])
@login_required
def add_patient():
    doctors = Doctor.query.all()
    rooms = Room.query.all()
    wards = Ward.query.all()
    if request.method == 'POST':
        f = request.form
        room_id = f.get('room_id') or None
        ward_id = f.get('ward_id') or None

        # Update room status
        if room_id:
            rm = db.session.get(Room, int(room_id))
            if rm:
                rm.status = 'Occupied'

        # Update ward bed counts
        if ward_id:
            wd = db.session.get(Ward, int(ward_id))
            if wd and wd.available_beds > 0:
                wd.available_beds -= 1
                wd.occupied_beds += 1

        patient = Patient(
            name=f['name'], age=int(f['age']), gender=f['gender'],
            blood_group=f.get('blood_group', ''),
            mobile=f['mobile'], email=f.get('email', ''),
            address=f.get('address', ''),
            emergency_contact=f.get('emergency_contact', ''),
            disease=f.get('disease', ''),
            doctor_id=f.get('doctor_id') or None,
            room_id=room_id, ward_id=ward_id,
            status='Admitted',
            admission_date=datetime.datetime.utcnow()
        )
        db.session.add(patient)
        db.session.commit()
        flash('Patient admitted successfully.', 'success')
        return redirect(url_for('patients'))
    return render_template('patient_form.html', action='Add', doctors=doctors, rooms=rooms, wards=wards, patient=None)


@app.route('/patients/<int:patient_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    doctors = Doctor.query.all()
    rooms = Room.query.all()
    wards = Ward.query.all()
    if request.method == 'POST':
        f = request.form
        patient.name = f['name']
        patient.age = int(f['age'])
        patient.gender = f['gender']
        patient.blood_group = f.get('blood_group', '')
        patient.mobile = f['mobile']
        patient.email = f.get('email', '')
        patient.address = f.get('address', '')
        patient.emergency_contact = f.get('emergency_contact', '')
        patient.disease = f.get('disease', '')
        patient.doctor_id = f.get('doctor_id') or None
        patient.room_id = f.get('room_id') or None
        patient.ward_id = f.get('ward_id') or None
        patient.status = f.get('status', 'Admitted')
        if patient.status == 'Discharged' and not patient.discharge_date:
            patient.discharge_date = datetime.datetime.utcnow()
            # Free room
            if patient.room_id:
                rm = db.session.get(Room, patient.room_id)
                if rm:
                    rm.status = 'Available'
            # Free ward bed
            if patient.ward_id:
                wd = db.session.get(Ward, patient.ward_id)
                if wd:
                    wd.available_beds = min(wd.capacity, wd.available_beds + 1)
                    wd.occupied_beds = max(0, wd.occupied_beds - 1)
        db.session.commit()
        flash('Patient record updated.', 'success')
        return redirect(url_for('patients'))
    return render_template('patient_form.html', action='Edit', doctors=doctors, rooms=rooms, wards=wards, patient=patient)


@app.route('/patients/<int:patient_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    # Free resources
    if patient.room_id:
        rm = db.session.get(Room, patient.room_id)
        if rm:
            rm.status = 'Available'
    if patient.ward_id:
        wd = db.session.get(Ward, patient.ward_id)
        if wd and patient.status == 'Admitted':
            wd.available_beds = min(wd.capacity, wd.available_beds + 1)
            wd.occupied_beds = max(0, wd.occupied_beds - 1)
    db.session.delete(patient)
    db.session.commit()
    flash('Patient deleted.', 'success')
    return redirect(url_for('patients'))


@app.route('/patients/<int:patient_id>/summary')
@login_required
def patient_summary(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    bills = Bill.query.filter_by(patient_id=patient_id).all()
    total_charges = sum(b.subtotal for b in bills)
    gst = total_charges * 0.05
    grand_total = total_charges + gst
    # Query medicines available for prescription
    medicines = Medicine.query.filter(Medicine.quantity > 0).all()
    return render_template('summary.html', patient=patient, bills=bills,
                           total_charges=total_charges, gst=gst, grand_total=grand_total,
                           medicines=medicines)


@app.route('/patients/<int:patient_id>/discharge', methods=['POST'])
@login_required
def discharge_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if patient.status == 'Discharged':
        flash('Patient is already discharged.', 'info')
        return redirect(url_for('patient_summary', patient_id=patient.id))

    patient.status = 'Discharged'
    patient.discharge_date = datetime.datetime.utcnow()

    # Free room
    if patient.room_id:
        rm = db.session.get(Room, patient.room_id)
        if rm:
            rm.status = 'Available'

    # Free ward bed
    if patient.ward_id:
        wd = db.session.get(Ward, patient.ward_id)
        if wd:
            wd.available_beds = min(wd.capacity, wd.available_beds + 1)
            wd.occupied_beds = max(0, wd.occupied_beds - 1)

    db.session.commit()
    flash('Patient discharged successfully.', 'success')
    return redirect(url_for('patient_summary', patient_id=patient.id))


@app.route('/patients/<int:patient_id>/prescribe', methods=['POST'])
@login_required
def prescribe_medicine(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    f = request.form
    medicine_id = int(f.get('medicine_id'))
    quantity = int(f.get('quantity', 1))
    instructions = f.get('instructions', '')

    med = db.session.get(Medicine, medicine_id)
    if not med:
        flash('Medicine not found.', 'danger')
        return redirect(url_for('patient_summary', patient_id=patient.id))

    if med.quantity < quantity:
        flash(f'Insufficient stock for {med.name}. Only {med.quantity} available.', 'danger')
        return redirect(url_for('patient_summary', patient_id=patient.id))

    # Create prescription
    prescription = Prescription(
        patient_id=patient.id,
        medicine_id=med.id,
        quantity=quantity,
        instructions=instructions
    )
    # Deduct stock
    med.quantity -= quantity

    db.session.add(prescription)
    db.session.commit()

    flash(f'Prescribed {quantity} of {med.name} successfully.', 'success')
    return redirect(url_for('patient_summary', patient_id=patient.id))


# ─── Doctors ─────────────────────────────────────────────────────────────────
@app.route('/doctors')
@login_required
def doctors():
    q = request.args.get('q', '')
    query = Doctor.query
    if q:
        query = query.filter(
            (Doctor.name.ilike(f'%{q}%')) |
            (Doctor.department.ilike(f'%{q}%'))
        )
    all_doctors = query.order_by(Doctor.name).all()
    return render_template('doctors.html', doctors=all_doctors, search=q)


@app.route('/doctors/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_doctor():
    if request.method == 'POST':
        f = request.form
        doc = Doctor(
            name=f['name'], department=f['department'],
            qualification=f['qualification'],
            experience=int(f.get('experience', 0)),
            contact=f['contact'], email=f.get('email', ''),
            availability=f.get('availability', 'Available'),
            salary=float(f.get('salary', 0))
        )
        db.session.add(doc)
        db.session.commit()
        flash('Doctor added.', 'success')
        return redirect(url_for('doctors'))
    return render_template('doctor_form.html', action='Add', doctor=None)


@app.route('/doctors/<int:doctor_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    if request.method == 'POST':
        f = request.form
        doctor.name = f['name']
        doctor.department = f['department']
        doctor.qualification = f['qualification']
        doctor.experience = int(f.get('experience', 0))
        doctor.contact = f['contact']
        doctor.email = f.get('email', '')
        doctor.availability = f.get('availability', 'Available')
        doctor.salary = float(f.get('salary', 0))
        db.session.commit()
        flash('Doctor updated.', 'success')
        return redirect(url_for('doctors'))
    return render_template('doctor_form.html', action='Edit', doctor=doctor)


@app.route('/doctors/<int:doctor_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    db.session.delete(doctor)
    db.session.commit()
    flash('Doctor removed.', 'success')
    return redirect(url_for('doctors'))


# ─── Nurses ──────────────────────────────────────────────────────────────────
@app.route('/nurses')
@login_required
def nurses():
    all_nurses = Nurse.query.order_by(Nurse.name).all()
    return render_template('nurses.html', nurses=all_nurses)


@app.route('/nurses/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_nurse():
    wards = Ward.query.all()
    if request.method == 'POST':
        f = request.form
        nurse = Nurse(
            name=f['name'], shift=f['shift'],
            contact=f['contact'], email=f.get('email', ''),
            ward_id=f.get('ward_id') or None
        )
        db.session.add(nurse)
        db.session.commit()
        flash('Nurse added.', 'success')
        return redirect(url_for('nurses'))
    return render_template('nurse_form.html', action='Add', nurse=None, wards=wards)


@app.route('/nurses/<int:nurse_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_nurse(nurse_id):
    nurse = Nurse.query.get_or_404(nurse_id)
    wards = Ward.query.all()
    if request.method == 'POST':
        f = request.form
        nurse.name = f['name']
        nurse.shift = f['shift']
        nurse.contact = f['contact']
        nurse.email = f.get('email', '')
        nurse.ward_id = f.get('ward_id') or None
        db.session.commit()
        flash('Nurse updated.', 'success')
        return redirect(url_for('nurses'))
    return render_template('nurse_form.html', action='Edit', nurse=nurse, wards=wards)


@app.route('/nurses/<int:nurse_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_nurse(nurse_id):
    nurse = Nurse.query.get_or_404(nurse_id)
    db.session.delete(nurse)
    db.session.commit()
    flash('Nurse removed.', 'success')
    return redirect(url_for('nurses'))


# ─── Wards ───────────────────────────────────────────────────────────────────
@app.route('/wards')
@login_required
def wards():
    all_wards = Ward.query.order_by(Ward.ward_number).all()
    return render_template('wards.html', wards=all_wards)


@app.route('/wards/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_ward():
    if request.method == 'POST':
        f = request.form
        cap = int(f.get('capacity', 10))
        ward = Ward(
            ward_number=f['ward_number'], ward_type=f['ward_type'],
            capacity=cap, available_beds=cap, occupied_beds=0
        )
        db.session.add(ward)
        db.session.commit()
        flash('Ward created.', 'success')
        return redirect(url_for('wards'))
    return render_template('ward_form.html', action='Add', ward=None)


@app.route('/wards/<int:ward_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_ward(ward_id):
    ward = Ward.query.get_or_404(ward_id)
    if request.method == 'POST':
        f = request.form
        ward.ward_number = f['ward_number']
        ward.ward_type = f['ward_type']
        ward.capacity = int(f.get('capacity', ward.capacity))
        db.session.commit()
        flash('Ward updated.', 'success')
        return redirect(url_for('wards'))
    return render_template('ward_form.html', action='Edit', ward=ward)


@app.route('/wards/<int:ward_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_ward(ward_id):
    ward = Ward.query.get_or_404(ward_id)
    db.session.delete(ward)
    db.session.commit()
    flash('Ward deleted.', 'success')
    return redirect(url_for('wards'))


@app.route('/wards/<int:ward_id>')
@login_required
def ward_detail(ward_id):
    ward = Ward.query.get_or_404(ward_id)
    return render_template('ward_detail.html', ward=ward)


# ─── Rooms ───────────────────────────────────────────────────────────────────
@app.route('/rooms')
@login_required
def rooms():
    rtype = request.args.get('type', '')
    query = Room.query
    if rtype:
        query = query.filter_by(room_type=rtype)
    all_rooms = query.order_by(Room.room_number).all()
    return render_template('rooms.html', rooms=all_rooms, selected_type=rtype)


@app.route('/rooms/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_room():
    if request.method == 'POST':
        f = request.form
        room = Room(
            room_number=f['room_number'], room_type=f['room_type'],
            floor=int(f.get('floor', 1)), status='Available',
            daily_rate=float(f.get('daily_rate', 500))
        )
        db.session.add(room)
        db.session.commit()
        flash('Room added.', 'success')
        return redirect(url_for('rooms'))
    return render_template('room_form.html', action='Add', room=None)


@app.route('/rooms/<int:room_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_room(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        f = request.form
        room.room_number = f['room_number']
        room.room_type = f['room_type']
        room.floor = int(f.get('floor', room.floor))
        room.status = f.get('status', room.status)
        room.daily_rate = float(f.get('daily_rate', room.daily_rate))
        db.session.commit()
        flash('Room updated.', 'success')
        return redirect(url_for('rooms'))
    return render_template('room_form.html', action='Edit', room=room)


@app.route('/rooms/<int:room_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_room(room_id):
    room = Room.query.get_or_404(room_id)
    db.session.delete(room)
    db.session.commit()
    flash('Room deleted.', 'success')
    return redirect(url_for('rooms'))


@app.route('/rooms/<int:room_id>')
@login_required
def room_detail(room_id):
    room = Room.query.get_or_404(room_id)
    return render_template('room_detail.html', room=room)


# ─── Appointments ────────────────────────────────────────────────────────────
@app.route('/appointments')
@login_required
def appointments():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    query = Appointment.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    pag = query.order_by(Appointment.date.desc(), Appointment.time).paginate(page=page, per_page=20, error_out=False)
    return render_template('appointments.html', appointments=pag, status_filter=status_filter)


@app.route('/appointments/add', methods=['GET', 'POST'])
@login_required
def add_appointment():
    patients_all = Patient.query.filter_by(status='Admitted').all()
    doctors_all = Doctor.query.all()
    if request.method == 'POST':
        f = request.form
        appt = Appointment(
            patient_id=int(f['patient_id']),
            doctor_id=int(f['doctor_id']),
            date=datetime.date.fromisoformat(f['date']),
            time=f['time'],
            notes=f.get('notes', ''),
            status='Scheduled'
        )
        db.session.add(appt)
        db.session.commit()
        flash('Appointment booked.', 'success')
        return redirect(url_for('appointments'))
    return render_template('appointment_form.html', action='Book',
                           appt=None, patients=patients_all, doctors=doctors_all)


@app.route('/appointments/<int:appt_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    patients_all = Patient.query.all()
    doctors_all = Doctor.query.all()
    if request.method == 'POST':
        f = request.form
        appt.patient_id = int(f['patient_id'])
        appt.doctor_id = int(f['doctor_id'])
        appt.date = datetime.date.fromisoformat(f['date'])
        appt.time = f['time']
        appt.notes = f.get('notes', '')
        appt.status = f.get('status', appt.status)
        db.session.commit()
        flash('Appointment updated.', 'success')
        return redirect(url_for('appointments'))
    return render_template('appointment_form.html', action='Edit',
                           appt=appt, patients=patients_all, doctors=doctors_all)


@app.route('/appointments/<int:appt_id>/cancel', methods=['POST'])
@login_required
def cancel_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    appt.status = 'Cancelled'
    db.session.commit()
    flash('Appointment cancelled.', 'info')
    return redirect(url_for('appointments'))


@app.route('/appointments/<int:appt_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    db.session.delete(appt)
    db.session.commit()
    flash('Appointment deleted.', 'success')
    return redirect(url_for('appointments'))


# ─── Medicines ───────────────────────────────────────────────────────────────
@app.route('/medicines')
@login_required
def medicines():
    q = request.args.get('q', '')
    query = Medicine.query
    if q:
        query = query.filter(Medicine.name.ilike(f'%{q}%'))
    all_meds = query.order_by(Medicine.name).all()
    today = datetime.date.today()
    return render_template('medicines.html', medicines=all_meds, search=q, today=today)


@app.route('/medicines/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'doctor')
def add_medicine():
    if request.method == 'POST':
        f = request.form
        med = Medicine(
            name=f['name'], batch_number=f['batch_number'],
            quantity=int(f['quantity']),
            expiry_date=datetime.date.fromisoformat(f['expiry_date']),
            price=float(f['price']),
            manufacturer=f.get('manufacturer', ''),
            category=f.get('category', '')
        )
        db.session.add(med)
        db.session.commit()
        flash('Medicine added.', 'success')
        return redirect(url_for('medicines'))
    return render_template('medicine_form.html', action='Add', med=None)


@app.route('/medicines/<int:med_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'doctor')
def edit_medicine(med_id):
    med = Medicine.query.get_or_404(med_id)
    if request.method == 'POST':
        f = request.form
        med.name = f['name']
        med.batch_number = f['batch_number']
        med.quantity = int(f['quantity'])
        med.expiry_date = datetime.date.fromisoformat(f['expiry_date'])
        med.price = float(f['price'])
        med.manufacturer = f.get('manufacturer', '')
        med.category = f.get('category', '')
        db.session.commit()
        flash('Medicine updated.', 'success')
        return redirect(url_for('medicines'))
    return render_template('medicine_form.html', action='Edit', med=med)


@app.route('/medicines/<int:med_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_medicine(med_id):
    med = Medicine.query.get_or_404(med_id)
    db.session.delete(med)
    db.session.commit()
    flash('Medicine deleted.', 'success')
    return redirect(url_for('medicines'))


# ─── Bills ───────────────────────────────────────────────────────────────────
@app.route('/bills')
@login_required
def bills():
    page = request.args.get('page', 1, type=int)
    all_bills = Bill.query.order_by(Bill.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('bills.html', bills=all_bills)


@app.route('/bills/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'receptionist')
def create_bill():
    all_patients = Patient.query.all()
    all_medicines = Medicine.query.all()
    if request.method == 'POST':
        f = request.form
        patient_id = int(f['patient_id'])
        bill_type = f.get('bill_type', 'Hospital')
        patient = db.session.get(Patient, patient_id)

        items = []
        subtotal = 0.0

        # Room charges
        if patient and patient.room and patient.admission_date:
            days = (datetime.datetime.utcnow() - patient.admission_date).days or 1
            room_charge = patient.room.daily_rate * days
            items.append({'description': f'Room {patient.room.room_number} ({days} days)',
                          'amount': room_charge})
            subtotal += room_charge

        # Doctor charge
        doctor_charge = float(f.get('doctor_charge', 0))
        if doctor_charge:
            items.append({'description': 'Doctor Consultation', 'amount': doctor_charge})
            subtotal += doctor_charge

        # Nurse charge
        nurse_charge = float(f.get('nurse_charge', 0))
        if nurse_charge:
            items.append({'description': 'Nursing Charges', 'amount': nurse_charge})
            subtotal += nurse_charge

        # Lab charge
        lab_charge = float(f.get('lab_charge', 0))
        if lab_charge:
            items.append({'description': 'Laboratory Charges', 'amount': lab_charge})
            subtotal += lab_charge

        # Medicine charges
        med_ids = f.getlist('medicine_ids')
        med_qtys = f.getlist('medicine_qtys')
        for mid, qty in zip(med_ids, med_qtys):
            if mid and qty:
                med = db.session.get(Medicine, int(mid))
                if med:
                    q = int(qty)
                    amt = med.price * q
                    items.append({'description': f'{med.name} x{q}', 'amount': amt})
                    subtotal += amt

        gst = round(subtotal * 0.05, 2)
        discount = float(f.get('discount', 0))
        total = round(subtotal + gst - discount, 2)

        bill_number = f'BILL{datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")}'
        bill = Bill(
            bill_number=bill_number, bill_type=bill_type,
            patient_id=patient_id, items_json=json.dumps(items),
            subtotal=round(subtotal, 2), gst=gst, discount=discount,
            total=total, payment_status='Pending'
        )
        db.session.add(bill)
        db.session.commit()
        flash(f'Bill {bill_number} created.', 'success')
        return redirect(url_for('view_bill', bill_id=bill.id))
    return render_template('bill_form.html', patients=all_patients, medicines=all_medicines)


@app.route('/bills/<int:bill_id>')
@login_required
def view_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    items = json.loads(bill.items_json) if bill.items_json else []
    return render_template('bill_view.html', bill=bill, items=items)


@app.route('/bills/<int:bill_id>/pay', methods=['POST'])
@login_required
@role_required('admin', 'receptionist')
def mark_bill_paid(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    bill.payment_status = 'Paid'
    db.session.commit()
    flash('Bill marked as paid.', 'success')
    return redirect(url_for('view_bill', bill_id=bill.id))


@app.route('/bills/<int:bill_id>/print')
@login_required
def print_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    items = json.loads(bill.items_json) if bill.items_json else []
    return render_template('bill_print.html', bill=bill, items=items)


@app.route('/bills/<int:bill_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    db.session.delete(bill)
    db.session.commit()
    flash('Bill deleted.', 'success')
    return redirect(url_for('bills'))


# ─── Reports ─────────────────────────────────────────────────────────────────
@app.route('/reports')
@login_required
@role_required('admin')
def reports():
    report_type = request.args.get('type', '')
    report_data = None
    today = datetime.date.today()

    if report_type == 'daily':
        start = datetime.datetime.combine(today, datetime.time.min)
        end = datetime.datetime.combine(today, datetime.time.max)
        pats = Patient.query.filter(Patient.admission_date.between(start, end)).all()
        revenue = db.session.query(db.func.sum(Bill.total)).filter(
            Bill.created_at.between(start, end)).scalar() or 0
        report_data = {'title': f'Daily Report – {today}', 'patients': pats, 'revenue': revenue}

    elif report_type == 'monthly':
        start = today.replace(day=1)
        pats = Patient.query.filter(
            Patient.admission_date >= datetime.datetime.combine(start, datetime.time.min)
        ).all()
        revenue = db.session.query(db.func.sum(Bill.total)).filter(
            Bill.created_at >= datetime.datetime.combine(start, datetime.time.min)
        ).scalar() or 0
        report_data = {'title': f'Monthly Report – {start.strftime("%B %Y")}',
                       'patients': pats, 'revenue': revenue}

    elif report_type == 'revenue':
        all_bills = Bill.query.order_by(Bill.created_at.desc()).all()
        total_rev = sum(b.total for b in all_bills)
        report_data = {'title': 'Revenue Report', 'bills': all_bills, 'total_revenue': total_rev}

    elif report_type == 'medicine':
        meds = Medicine.query.order_by(Medicine.quantity).all()
        report_data = {'title': 'Medicine Stock Report', 'medicines': meds}

    elif report_type == 'patient':
        pats = Patient.query.order_by(Patient.admission_date.desc()).all()
        report_data = {'title': 'All Patients Report', 'patients': pats}

    return render_template('reports.html', report_type=report_type, report=report_data)


@app.route('/reports/export')
@login_required
@role_required('admin')
def download_report():
    fmt = request.args.get('fmt', 'excel')
    report_type = request.args.get('type', 'patient')

    if fmt == 'excel':
        import openpyxl
        from io import BytesIO
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = report_type.capitalize()

        if report_type == 'patient':
            ws.append(['ID', 'Name', 'Age', 'Gender', 'Disease', 'Status', 'Admission'])
            for p in Patient.query.all():
                ws.append([p.id, p.name, p.age, p.gender, p.disease, p.status,
                           p.admission_date.strftime('%Y-%m-%d')])
        elif report_type == 'revenue':
            ws.append(['Bill No', 'Patient', 'Type', 'Total', 'Status', 'Date'])
            for b in Bill.query.all():
                ws.append([b.bill_number, b.patient.name, b.bill_type,
                           b.total, b.payment_status, b.created_at.strftime('%Y-%m-%d')])
        elif report_type == 'medicine':
            ws.append(['ID', 'Name', 'Batch', 'Qty', 'Expiry', 'Price'])
            for m in Medicine.query.all():
                ws.append([m.id, m.name, m.batch_number, m.quantity,
                           m.expiry_date.strftime('%Y-%m-%d'), m.price])

        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        resp = make_response(buf.read())
        resp.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        resp.headers['Content-Disposition'] = f'attachment; filename={report_type}_report.xlsx'
        return resp


# ─── API – Live Dashboard ─────────────────────────────────────────────────────
@app.route('/api/stats')
@login_required
def api_stats():
    return jsonify({
        'total_patients': Patient.query.count(),
        'admitted_patients': Patient.query.filter_by(status='Admitted').count(),
        'discharged_patients': Patient.query.filter_by(status='Discharged').count(),
        'total_doctors': Doctor.query.count(),
        'total_nurses': Nurse.query.count(),
        'available_rooms': Room.query.filter_by(status='Available').count(),
        'available_beds': db.session.query(db.func.sum(Ward.available_beds)).scalar() or 0,
        'revenue': db.session.query(db.func.sum(Bill.total)).scalar() or 0.0,
    })


@app.route('/api/beds')
@login_required
def api_beds():
    wards = Ward.query.all()
    return jsonify([{
        'ward': w.ward_number, 'type': w.ward_type,
        'capacity': w.capacity, 'available': w.available_beds,
        'occupied': w.occupied_beds
    } for w in wards])


@app.route('/api/recent_appointments')
@login_required
def api_recent_appointments():
    appts = Appointment.query.order_by(Appointment.created_at.desc()).limit(5).all()
    return jsonify([{
        'id': a.id, 'patient': a.patient.name, 'doctor': a.doctor.name,
        'date': str(a.date), 'time': a.time, 'status': a.status
    } for a in appts])


@app.route('/api/patients/<int:patient_id>/prescriptions')
@login_required
def api_patient_prescriptions(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    prescriptions = Prescription.query.filter_by(patient_id=patient_id).all()
    return jsonify([{
        'medicine_id': p.medicine_id,
        'medicine_name': p.medicine.name,
        'price': p.medicine.price,
        'quantity': p.quantity
    } for p in prescriptions])


@app.route('/patients/<int:patient_id>/pdf')
@login_required
def patient_pdf(patient_id):
    from io import BytesIO
    from flask import send_file
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    patient = Patient.query.get_or_404(patient_id)
    bills = Bill.query.filter_by(patient_id=patient_id).all()
    total_charges = sum(b.subtotal for b in bills)
    gst = total_charges * 0.05
    grand_total = total_charges + gst

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=15
    )
    h2_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=colors.HexColor('#1e40af'),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    label_style = ParagraphStyle(
        'GridLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.HexColor('#334155')
    )
    value_style = ParagraphStyle(
        'GridValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#0f172a')
    )
    badge_style_admitted = ParagraphStyle(
        'BadgeAdmitted',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.HexColor('#15803d')
    )
    badge_style_discharged = ParagraphStyle(
        'BadgeDischarged',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.HexColor('#b91c1c')
    )

    # Title & Header
    story.append(Paragraph("Hospital+ HMS", title_style))
    story.append(Paragraph("Patient Summary Report | 123 Healthcare Blvd | +1 (555) 019-9000", subtitle_style))
    
    # Section 1: Personal Details
    story.append(Paragraph("Personal Details", h2_style))
    
    status_style = badge_style_discharged if patient.status == 'Discharged' else badge_style_admitted
    
    personal_data = [
        [
            Paragraph("Patient ID:", label_style), Paragraph(f"#{patient.id}", value_style),
            Paragraph("Full Name:", label_style), Paragraph(patient.name, value_style)
        ],
        [
            Paragraph("Age:", label_style), Paragraph(str(patient.age), value_style),
            Paragraph("Gender:", label_style), Paragraph(patient.gender, value_style)
        ],
        [
            Paragraph("Blood Group:", label_style), Paragraph(patient.blood_group or "—", value_style),
            Paragraph("Mobile:", label_style), Paragraph(patient.mobile, value_style)
        ],
        [
            Paragraph("Email:", label_style), Paragraph(patient.email or "—", value_style),
            Paragraph("Emergency Contact:", label_style), Paragraph(patient.emergency_contact or "—", value_style)
        ],
        [
            Paragraph("Admission Date:", label_style), Paragraph(patient.admission_date.strftime('%d %b %Y, %H:%M') if patient.admission_date else "—", value_style),
            Paragraph("Discharge Date:", label_style), Paragraph(patient.discharge_date.strftime('%d %b %Y, %H:%M') if patient.discharge_date else "—", value_style)
        ],
        [
            Paragraph("Status:", label_style), Paragraph(patient.status, status_style),
            Paragraph("Address:", label_style), Paragraph(patient.address or "—", value_style)
        ]
    ]
    t1 = Table(personal_data, colWidths=[100, 170, 100, 170])
    t1.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(t1)
    story.append(Spacer(1, 10))

    # Section 2: Treatment Information
    story.append(Paragraph("Treatment Details", h2_style))
    treatment_data = [
        [Paragraph("Diagnosis / Disease:", label_style), Paragraph(patient.disease or "—", value_style)],
        [Paragraph("Assigned Doctor:", label_style), Paragraph(f"{patient.doctor.name} ({patient.doctor.department})" if patient.doctor else "—", value_style)],
        [Paragraph("Ward Allocated:", label_style), Paragraph(f"Ward {patient.ward.ward_number} ({patient.ward.ward_type})" if patient.ward else "—", value_style)],
        [Paragraph("Room Allocated:", label_style), Paragraph(f"Room {patient.room.room_number} ({patient.room.room_type})" if patient.room else "—", value_style)]
    ]
    t2 = Table(treatment_data, colWidths=[150, 390])
    t2.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(t2)
    story.append(Spacer(1, 10))

    # Section 3: Prescriptions
    story.append(Paragraph("Prescribed Medicines", h2_style))
    presc_headers = [Paragraph("Medicine", label_style), Paragraph("Quantity", label_style), Paragraph("Instructions", label_style), Paragraph("Date", label_style)]
    presc_data = [presc_headers]
    for p in patient.prescriptions:
        presc_data.append([
            Paragraph(p.medicine.name, value_style),
            Paragraph(str(p.quantity), value_style),
            Paragraph(p.instructions or "—", value_style),
            Paragraph(p.created_at.strftime('%d %b %Y') if p.created_at else "—", value_style)
        ])
    if len(presc_data) == 1:
        presc_data.append([Paragraph("No medicines prescribed.", value_style), "", "", ""])
    t3 = Table(presc_data, colWidths=[160, 60, 220, 100])
    t3.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
        ('SPAN', (0,1), (3,1)) if len(presc_data) == 2 and presc_data[1][1] == "" else ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    story.append(t3)
    story.append(Spacer(1, 10))

    # Section 4: Billing Summary
    story.append(Paragraph("Billing & Invoices", h2_style))
    bill_headers = [Paragraph("Bill No.", label_style), Paragraph("Type", label_style), Paragraph("Status", label_style), Paragraph("Total", label_style)]
    bill_data = [bill_headers]
    for b in bills:
        bill_data.append([
            Paragraph(b.bill_number, value_style),
            Paragraph(b.bill_type, value_style),
            Paragraph(b.payment_status, value_style),
            Paragraph(f"INR {b.total:.2f}", value_style)
        ])
    
    # Summary totals rows
    bill_data.append([Paragraph("Subtotal", label_style), "", "", Paragraph(f"INR {total_charges:.2f}", label_style)])
    bill_data.append([Paragraph("GST (5%)", label_style), "", "", Paragraph(f"INR {gst:.2f}", label_style)])
    bill_data.append([Paragraph("Grand Total", label_style), "", "", Paragraph(f"INR {grand_total:.2f}", label_style)])
    
    t4 = Table(bill_data, colWidths=[150, 120, 120, 150])
    t4_style = [
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
        ('GRID', (0,0), (-1,-len(bills)-1), 0.5, colors.HexColor('#e2e8f0')),
        ('SPAN', (0, -3), (2, -3)),
        ('SPAN', (0, -2), (2, -2)),
        ('SPAN', (0, -1), (2, -1)),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0fdf4')),
        ('GRID', (0, -3), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]
    t4.setStyle(TableStyle(t4_style))
    story.append(t4)

    doc.build(story)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Patient_Summary_{patient.id}.pdf",
        mimetype="application/pdf"
    )


@app.route('/bills/<int:bill_id>/pdf')
@login_required
def bill_pdf(bill_id):
    from io import BytesIO
    from flask import send_file
    import json
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    bill = Bill.query.get_or_404(bill_id)
    items = json.loads(bill.items_json) if bill.items_json else []

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=15
    )
    h2_style = ParagraphStyle(
        'InvoiceHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=10,
        spaceAfter=10
    )
    label_style = ParagraphStyle(
        'GridLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.HexColor('#334155')
    )
    value_style = ParagraphStyle(
        'GridValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#0f172a')
    )

    story.append(Paragraph("Hospital+ HMS", title_style))
    story.append(Paragraph("In-patient Billing Department | Invoice Generation", subtitle_style))
    
    story.append(Paragraph(f"INVOICE {bill.bill_number}", h2_style))
    
    info_data = [
        [
            Paragraph("Bill Number:", label_style), Paragraph(bill.bill_number, value_style),
            Paragraph("Date Issued:", label_style), Paragraph(bill.created_at.strftime('%d %b %Y') if bill.created_at else "—", value_style)
        ],
        [
            Paragraph("Patient Name:", label_style), Paragraph(bill.patient.name, value_style),
            Paragraph("Mobile:", label_style), Paragraph(bill.patient.mobile, value_style)
        ],
        [
            Paragraph("Bill Type:", label_style), Paragraph(bill.bill_type, value_style),
            Paragraph("Payment Status:", label_style), Paragraph(bill.payment_status, label_style)
        ]
    ]
    t_info = Table(info_data, colWidths=[100, 170, 100, 170])
    t_info.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 15))
    
    # Items table
    item_headers = [Paragraph("#", label_style), Paragraph("Description", label_style), Paragraph("Amount", label_style)]
    item_data = [item_headers]
    for idx, item in enumerate(items):
        item_data.append([
            Paragraph(str(idx + 1), value_style),
            Paragraph(item.get('description', ''), value_style),
            Paragraph(f"INR {item.get('amount', 0.0):.2f}", value_style)
        ])
    
    # Summary totals rows
    item_data.append(["", Paragraph("Subtotal", label_style), Paragraph(f"INR {bill.subtotal:.2f}", label_style)])
    item_data.append(["", Paragraph("GST (5%)", label_style), Paragraph(f"INR {bill.gst:.2f}", label_style)])
    if bill.discount:
        item_data.append(["", Paragraph("Discount", label_style), Paragraph(f"-INR {bill.discount:.2f}", label_style)])
    item_data.append(["", Paragraph("Grand Total", label_style), Paragraph(f"INR {bill.total:.2f}", label_style)])
    
    t_items = Table(item_data, colWidths=[40, 350, 150])
    t_items_style = [
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
        ('GRID', (0,0), (-1,-len(items)-1), 0.5, colors.HexColor('#e2e8f0')),
        ('SPAN', (0, -4), (1, -4)) if not bill.discount else ('SPAN', (0, -5), (1, -5)),
        ('SPAN', (0, -3), (1, -3)),
        ('SPAN', (0, -2), (1, -2)),
        ('SPAN', (0, -1), (1, -1)),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0fdf4')),
        ('GRID', (0, -4 if not bill.discount else -5), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]
    t_items.setStyle(TableStyle(t_items_style))
    story.append(t_items)
    
    story.append(Spacer(1, 20))
    story.append(Paragraph("Thank you for choosing Hospital+ HMS. Wishing you a speedy recovery!", subtitle_style))
    
    doc.build(story)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Invoice_{bill.bill_number}.pdf",
        mimetype="application/pdf"
    )


# ─── Seed Data ────────────────────────────────────────────────────────────────
def seed_data():
    if User.query.first():
        return

    import random

    # Users
    admin = User(username='admin', email='admin@hospital.com', full_name='Admin User', role='admin')
    admin.set_password('admin123')
    db.session.add(admin)
    db.session.flush()

    # Doctors
    depts = ['Cardiology', 'Neurology', 'Orthopedics', 'Pediatrics', 'General Medicine']
    quals = ['MBBS, MD', 'MBBS, MS', 'MBBS, DM', 'MBBS, MCh', 'MBBS']
    doctor_names = ['Dr. Arjun Sharma', 'Dr. Priya Verma', 'Dr. Ravi Kumar',
                    'Dr. Sunita Patel', 'Dr. Anjali Mehta']
    doctors_created = []
    for i, name in enumerate(doctor_names):
        doc = Doctor(
            name=name, department=depts[i], qualification=quals[i],
            experience=random.randint(3, 20),
            contact=f'98{random.randint(10000000, 99999999)}',
            email=f'dr{i+1}@hospital.com',
            availability='Available',
            salary=random.randint(80000, 200000)
        )
        db.session.add(doc)
        doctors_created.append(doc)
    db.session.flush()

    # Wards
    ward_types = ['General', 'ICU', 'Pediatric', 'Surgical', 'Maternity']
    wards_created = []
    for i, wt in enumerate(ward_types):
        ward = Ward(
            ward_number=f'W{i+1:02}', ward_type=wt,
            capacity=10, available_beds=10, occupied_beds=0
        )
        db.session.add(ward)
        wards_created.append(ward)
    db.session.flush()

    # Nurses
    shifts = ['Morning', 'Afternoon', 'Night']
    nurse_names = ['Nurse Meena Singh', 'Nurse Kavya Reddy', 'Nurse Deepa Nair',
                   'Nurse Pooja Tiwari', 'Nurse Asha Gupta']
    for i, name in enumerate(nurse_names):
        nurse = Nurse(
            name=name, shift=shifts[i % 3],
            contact=f'97{random.randint(10000000, 99999999)}',
            email=f'nurse{i+1}@hospital.com',
            ward_id=wards_created[i % len(wards_created)].id
        )
        db.session.add(nurse)

    # Rooms
    room_types = ['General', 'Semi-Private', 'Private', 'ICU']
    rates = {'General': 500, 'Semi-Private': 1000, 'Private': 2000, 'ICU': 5000}
    rooms_created = []
    for floor in range(1, 4):
        for j, rtype in enumerate(room_types):
            room = Room(
                room_number=f'{floor}{j+1:02}',
                room_type=rtype, floor=floor,
                status='Available',
                daily_rate=rates[rtype]
            )
            db.session.add(room)
            rooms_created.append(room)
    db.session.flush()

    # Patients
    diseases = ['Typhoid', 'Malaria', 'Hypertension', 'Diabetes', 'Appendicitis',
                'Pneumonia', 'Fracture', 'Asthma', 'Dengue', 'Migraine']
    blood_groups = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']
    patient_names = [
        'Rahul Gupta', 'Priya Sharma', 'Amit Singh', 'Sunita Patel', 'Rohan Verma',
        'Neha Joshi', 'Suresh Kumar', 'Kavitha Reddy', 'Arjun Nair', 'Deepa Mehta'
    ]
    patients_created = []
    for i, pname in enumerate(patient_names):
        doc = doctors_created[i % len(doctors_created)]
        room = rooms_created[i]
        ward = wards_created[i % len(wards_created)]

        # Update room & ward
        room.status = 'Occupied'
        ward.available_beds = max(0, ward.available_beds - 1)
        ward.occupied_beds += 1

        admission = datetime.datetime.utcnow() - datetime.timedelta(days=random.randint(1, 10))
        pat = Patient(
            name=pname,
            age=random.randint(15, 75),
            gender='Male' if i % 2 == 0 else 'Female',
            blood_group=random.choice(blood_groups),
            mobile=f'96{random.randint(10000000, 99999999)}',
            email=f'patient{i+1}@example.com',
            address=f'{i+10} Main Street, City',
            emergency_contact=f'95{random.randint(10000000, 99999999)}',
            disease=diseases[i],
            doctor_id=doc.id, room_id=room.id, ward_id=ward.id,
            status='Admitted', admission_date=admission
        )
        db.session.add(pat)
        patients_created.append(pat)
    db.session.flush()

    # Appointments
    for i in range(5):
        pat = patients_created[i]
        doc = doctors_created[i % len(doctors_created)]
        appt = Appointment(
            patient_id=pat.id, doctor_id=doc.id,
            date=datetime.date.today() + datetime.timedelta(days=i),
            time=f'{9+i}:00',
            status='Scheduled', notes='Follow-up consultation'
        )
        db.session.add(appt)

    # Medicines
    med_list = [
        ('Paracetamol', 'BATCH001', 100, 25.0, 'Analgesic'),
        ('Amoxicillin', 'BATCH002', 50, 120.0, 'Antibiotic'),
        ('Metformin', 'BATCH003', 80, 45.0, 'Antidiabetic'),
        ('Atorvastatin', 'BATCH004', 60, 95.0, 'Cholesterol'),
        ('Omeprazole', 'BATCH005', 70, 60.0, 'Antacid'),
        ('Ibuprofen', 'BATCH006', 90, 35.0, 'NSAID'),
        ('Cetirizine', 'BATCH007', 40, 55.0, 'Antihistamine'),
        ('Aspirin', 'BATCH008', 120, 20.0, 'Blood Thinner'),
        ('Salbutamol', 'BATCH009', 30, 150.0, 'Bronchodilator'),
        ('Dexamethasone', 'BATCH010', 25, 200.0, 'Steroid'),
        ('Ranitidine', 'BATCH011', 3, 75.0, 'Antacid'),  # Low stock
        ('Diazepam', 'BATCH012', 2, 180.0, 'Sedative'),  # Low stock
    ]
    for name, batch, qty, price, cat in med_list:
        med = Medicine(
            name=name, batch_number=batch, quantity=qty,
            expiry_date=datetime.date.today() + datetime.timedelta(days=random.randint(60, 365)),
            price=price, manufacturer='PharmaCo', category=cat
        )
        db.session.add(med)

    # Sample bills
    for i, pat in enumerate(patients_created[:5]):
        items = [
            {'description': f'Room charges (5 days)', 'amount': 2500.0},
            {'description': 'Doctor Consultation', 'amount': 1000.0},
        ]
        subtotal = 3500.0
        gst = round(subtotal * 0.05, 2)
        bill = Bill(
            bill_number=f'BILL2026{i+1:04}',
            bill_type='Hospital', patient_id=pat.id,
            items_json=json.dumps(items),
            subtotal=subtotal, gst=gst, discount=0,
            total=round(subtotal + gst, 2),
            payment_status='Pending'
        )
        db.session.add(bill)

    db.session.commit()
    print('[OK] Seed data inserted successfully.')


# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=True, host='0.0.0.0', port=5000)
