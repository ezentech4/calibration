import os
import logging
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
from datetime import datetime, timedelta
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from flask_wtf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///calibration.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "connect_args": {"sslmode": "require"} if "postgresql" in os.environ.get("DATABASE_URL", "") else {}
}
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
CORS(app)

# Initialize SQLAlchemy
db = SQLAlchemy(app)
csrf = CSRFProtect(app)

# Database Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(100))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Department(db.Model):
    __tablename__ = 'departments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    manager_email = db.Column(db.String(120))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Instrument(db.Model):
    __tablename__ = 'instruments'
    __table_args__ = (
        db.Index('idx_last_calibration_date', 'last_calibration_date'),
        db.Index('idx_department_id', 'department_id'),
    )
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    serial_number = db.Column(db.String(100))
    manufacturer = db.Column(db.String(100))
    model = db.Column(db.String(100))
    location = db.Column(db.String(200))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    last_calibration_date = db.Column(db.Date, nullable=False)
    calibration_frequency = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.String(50), default='active')  # active, out_of_service, repair
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    department = db.relationship('Department', backref='instruments')

class Repair(db.Model):
    __tablename__ = 'repairs'
    id = db.Column(db.Integer, primary_key=True)
    instrument_id = db.Column(db.Integer, db.ForeignKey('instruments.id'), nullable=False)
    repair_type = db.Column(db.String(50), nullable=False)  # maintenance, repair, replacement
    description = db.Column(db.Text, nullable=False)
    cost = db.Column(db.Numeric(10, 2))
    technician = db.Column(db.String(100))
    start_date = db.Column(db.Date, nullable=False)
    completion_date = db.Column(db.Date)
    status = db.Column(db.String(50), default='in_progress')  # in_progress, completed, cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    instrument = db.relationship('Instrument', backref='repairs')

class Reminder(db.Model):
    __tablename__ = 'reminders'
    id = db.Column(db.Integer, primary_key=True)
    instrument_id = db.Column(db.Integer, db.ForeignKey('instruments.id'), nullable=False)
    reminder_date = db.Column(db.Date, nullable=False)
    reminder_type = db.Column(db.String(50), default='calibration')  # calibration, maintenance
    status = db.Column(db.String(50), default='pending')  # pending, sent, acknowledged
    email_sent = db.Column(db.Boolean, default=False)
    sent_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    instrument = db.relationship('Instrument', backref='reminders')

# Legacy SQLite support
DATABASE_NAME = 'calibration.db'

def get_db_connection():
    """Create and return database connection with row factory"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# Authentication functions
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Admin access required', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Email functions
def send_email_reminder(to_email, subject, content, instrument_name):
    """Send email reminder using SendGrid"""
    try:
        sendgrid_key = os.environ.get('SENDGRID_API_KEY')
        if not sendgrid_key:
            logging.warning("SENDGRID_API_KEY not configured")
            return False
            
        sg = SendGridAPIClient(sendgrid_key)
        from_email = os.environ.get('FROM_EMAIL', 'calibration@company.com')
        
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=content
        )
        
        response = sg.send(message)
        logging.info(f"Email sent to {to_email}, status: {response.status_code}")
        return True
    except Exception as e:
        logging.error(f"Email sending error: {e}")
        return False

def init_database():
    """Initialize database tables"""
    try:
        with app.app_context():
            db.create_all()
            
            # Create default admin user if none exists
            if not User.query.filter_by(is_admin=True).first():
                admin_user = User()
                admin_user.username = 'admin'
                admin_user.email = 'admin@company.com'
                admin_user.password_hash = generate_password_hash('admin123')
                admin_user.department = 'IT'
                admin_user.is_admin = True
                db.session.add(admin_user)
                
            # Create default departments
            if not Department.query.first():
                dept1 = Department()
                dept1.name = 'Laboratory'
                dept1.description = 'Laboratory equipment'
                db.session.add(dept1)
                
                dept2 = Department()
                dept2.name = 'Production'
                dept2.description = 'Production line equipment'
                db.session.add(dept2)
                
                dept3 = Department()
                dept3.name = 'Quality Control'
                dept3.description = 'QC instruments'
                db.session.add(dept3)
                
                dept4 = Department()
                dept4.name = 'Maintenance'
                dept4.description = 'Maintenance tools'
                db.session.add(dept4)
            
            db.session.commit()
            logging.info("Database tables initialized successfully")
    except Exception as e:
        logging.error(f"Database initialization error: {e}")

# Initialize database after models are defined
init_database()

def calculate_calibration_status(last_calibration_date, frequency_days):
    """Calculate calibration status based on dates"""
    try:
        if isinstance(last_calibration_date, str):
            last_date = datetime.strptime(last_calibration_date, '%Y-%m-%d').date()
        elif isinstance(last_calibration_date, datetime):
            last_date = last_calibration_date.date()
        else:
            last_date = last_calibration_date

        next_date = last_date + timedelta(days=frequency_days)
        today = datetime.now().date()
        days_until = (next_date - today).days

        if days_until < 0:
            return 'overdue', abs(days_until)
        elif days_until <= 30:
            return 'upcoming', days_until
        else:
            return 'current', days_until
    except Exception as e:
        logging.error(f"Error calculating status: {e}")
        return 'unknown', 0

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and password and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html', form=None)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        department = request.form.get('department')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('register.html', departments=Department.query.all())
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('register.html', departments=Department.query.all())
        
        if not password or len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('register.html', departments=Department.query.all())
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            department=department
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', departments=Department.query.all())

# Main Routes
@app.route('/')
@app.route('/dashboard')
def dashboard():
    """Main dashboard showing calibration overview"""
    try:
        # Get instruments with their department info
        instruments = db.session.query(Instrument).join(Department, isouter=True).order_by(Instrument.last_calibration_date.asc()).all()
        
        # Calculate stats
        all_instruments = Instrument.query.all()
        overdue_count = 0
        upcoming_count = 0
        current_count = 0
        repair_count = Repair.query.filter_by(status='in_progress').count()
        
        instrument_data = []
        for instrument in instruments:
            status, days = calculate_calibration_status(
                instrument.last_calibration_date, 
                instrument.calibration_frequency
            )
            
            instrument_dict = {
                'id': instrument.id,
                'name': instrument.name,
                'manufacturer': instrument.manufacturer,
                'model': instrument.model,
                'department': instrument.department.name if instrument.department else 'No Department',
                'last_calibration_date': instrument.last_calibration_date,
                'status': status,
                'days_info': days
            }
            instrument_data.append(instrument_dict)
        
        # Count all statuses
        for instrument in all_instruments:
            status, _ = calculate_calibration_status(
                instrument.last_calibration_date, 
                instrument.calibration_frequency
            )
            if status == 'overdue':
                overdue_count += 1
            elif status == 'upcoming':
                upcoming_count += 1
            else:
                current_count += 1
        
        stats = {
            'total': len(all_instruments),
            'overdue': overdue_count,
            'upcoming': upcoming_count,
            'current': current_count,
            'repairs': repair_count
        }
        
        return render_template('dashboard.html', 
            instruments=instrument_data,
            stats=stats,
            user=User.query.get(session.get('user_id')))
    except Exception as e:
        logging.error(f"Dashboard error: {e}")
        flash(f'Error loading dashboard: {str(e)}', 'danger')
        return render_template('dashboard.html', instruments=[], stats={})

# Instruments route
@app.route('/instruments')
@login_required
def instruments():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM instruments ORDER BY name ASC')
            instruments = cursor.fetchall()
            # If using sqlite3.Row, pass as list of dicts for template compatibility
            instruments = [dict(row) for row in instruments]
            return render_template('instruments.html', instruments=instruments)
    except Exception as e:
        import logging
        logging.error(f"Instruments page error: {e}")
        flash('Error loading instruments.', 'danger')
        return render_template('instruments.html', instruments=[])

@app.route('/instruments/add', methods=['GET', 'POST'])
def add_instrument():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            serial_number = request.form.get('serial_number', '').strip()
            manufacturer = request.form.get('manufacturer', '').strip()
            model = request.form.get('model', '').strip()
            location = request.form.get('location', '').strip()
            last_calibration_date = request.form.get('last_calibration_date')
            calibration_frequency = int(request.form.get('calibration_frequency', 0))
            notes = request.form.get('notes', '').strip()
            department_id = request.form.get('department_id')

            if not name or not last_calibration_date or calibration_frequency <= 0:
                flash('Name, last calibration date, and valid frequency are required.', 'danger')
                return render_template('add_instrument.html')

            instrument = Instrument(
                name=name,
                serial_number=serial_number,
                manufacturer=manufacturer,
                model=model,
                location=location,
                last_calibration_date=datetime.strptime(last_calibration_date, '%Y-%m-%d').date(),
                calibration_frequency=calibration_frequency,
                notes=notes,
                department_id=department_id if department_id else None,
                status='active'
            )
            db.session.add(instrument)
            db.session.commit()
            flash(f'Instrument "{name}" added successfully!', 'success')
            return redirect(url_for('instruments'))
        except Exception as e:
            flash(f'Error adding instrument: {str(e)}', 'danger')

    departments = Department.query.order_by(Department.name).all()
    return render_template('add_instrument.html', departments=departments)

@app.route('/instruments/<int:instrument_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_instrument(instrument_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM instruments WHERE id = ?', (instrument_id,))
        instrument = cursor.fetchone()
        if not instrument:
            flash('Instrument not found.', 'error')
            return redirect(url_for('instruments'))
        if request.method == 'POST':
            try:
                data = request.form
                name = data.get('name', '').strip()
                serial_number = data.get('serial_number', '').strip()
                manufacturer = data.get('manufacturer', '').strip()
                model = data.get('model', '').strip()
                location = data.get('location', '').strip()
                last_calibration_date = data.get('last_calibration_date')
                calibration_frequency = int(data.get('calibration_frequency', 0))
                notes = data.get('notes', '').strip()
                
                if not name or not last_calibration_date or calibration_frequency <= 0:
                    flash('Name, last calibration date, and valid frequency are required.', 'danger')
                    return render_template('edit_instrument.html', instrument=dict(instrument))
                
                cursor.execute('''
                    UPDATE instruments 
                    SET name=?, serial_number=?, manufacturer=?, model=?, location=?,
                        last_calibration_date=?, calibration_frequency=?, notes=?,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=?''',
                    (name, serial_number, manufacturer, model, location,
                     last_calibration_date, calibration_frequency, notes, instrument_id))
                conn.commit()
                flash(f'Instrument "{name}" updated successfully!', 'success')
                return redirect(url_for('instruments'))
            except ValueError:
                flash('Please enter a valid calibration frequency (number of days).', 'danger')
                return render_template('edit_instrument.html', instrument=dict(instrument))
            except Exception as e:
                logging.error(f"Edit instrument error: {e}")
                flash('An unexpected error occurred while editing the instrument.', 'danger')
                return render_template('edit_instrument.html', instrument=dict(instrument))
        
    return render_template('edit_instrument.html', instrument=dict(instrument))

@app.route('/instruments/<int:instrument_id>/calibrate', methods=['POST'])
def calibrate_instrument(instrument_id):
    """Mark instrument as calibrated with new date"""
    try:
        calibration_date = request.form.get('calibration_date')
        if not calibration_date:
            calibration_date = datetime.now().strftime('%Y-%m-%d')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE instruments 
                SET last_calibration_date=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?''',
                (calibration_date, instrument_id))
            
            if cursor.rowcount == 0:
                flash('Instrument not found.', 'danger')
            else:
                conn.commit()
                flash('Instrument calibration date updated successfully!', 'success')
                
    except Exception as e:
        logging.error(f"Calibrate instrument error: {e}")
        flash(f'Error updating calibration: {str(e)}', 'danger')
    
    return redirect(url_for('instruments'))

@app.route('/instruments/<int:instrument_id>/delete', methods=['POST'])
@login_required
def delete_instrument(instrument_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM instruments WHERE id = ?', (instrument_id,))
            conn.commit()
            flash('Instrument deleted successfully.', 'success')
    except Exception as e:
        import logging
        logging.error(f"Delete instrument error: {e}")
        flash('Error deleting instrument.', 'danger')
    return redirect(url_for('instruments'))

@app.route('/repairs')
@login_required
def repairs():
    """Show all repairs"""
    try:
        search = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        
        query = db.session.query(Repair).join(Instrument)
        
        if search:
            query = query.filter(
                db.or_(
                    Instrument.name.contains(search),
                    Repair.description.contains(search),
                    Repair.technician.contains(search)
                )
            )
        
        if status_filter:
            query = query.filter(Repair.status == status_filter)
        
        repairs_list = query.order_by(Repair.start_date.desc()).all()
        
        repair_data = []
        for repair in repairs_list:
            repair_dict = {
                'id': repair.id,
                'instrument_name': repair.instrument.name,
                'repair_type': repair.repair_type,
                'description': repair.description,
                'cost': repair.cost,
                'technician': repair.technician,
                'start_date': repair.start_date,
                'completion_date': repair.completion_date,
                'status': repair.status,
                'notes': repair.notes
            }
            repair_data.append(repair_dict)
        
        return render_template('repairs.html', 
                             repairs=repair_data,
                             search=search,
                             status_filter=status_filter)
    except Exception as e:
        logging.error(f"Repairs page error: {e}")
        flash(f'Error loading repairs: {str(e)}', 'danger')
        return render_template('repairs.html', repairs=[])

@app.route('/add_repair', methods=['GET', 'POST'])
@login_required
def add_repair():
    """Add new repair"""
    if request.method == 'POST':
        try:
            repair = Repair()
            repair.instrument_id = request.form.get('instrument_id')
            repair.repair_type = request.form.get('repair_type')
            repair.description = request.form.get('description')
            repair.cost = request.form.get('cost') or None
            repair.technician = request.form.get('technician')
            start_date = request.form.get('start_date')
            if start_date:
                repair.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            else:
                repair.start_date = datetime.now().date()
            repair.notes = request.form.get('notes')
            
            db.session.add(repair)
            db.session.commit()
            
            flash('Repair record added successfully!', 'success')
            return redirect(url_for('repairs'))
        except Exception as e:
            logging.error(f"Add repair error: {e}")
            flash(f'Error adding repair: {str(e)}', 'danger')
    
    instruments = Instrument.query.order_by(Instrument.name).all()
    return render_template('add_repair.html', 
                         instruments=instruments,
                         current_date=datetime.now().strftime('%Y-%m-%d'))

@app.route('/complete_repair/<int:repair_id>', methods=['POST'])
@login_required
def complete_repair(repair_id):
    """Mark repair as completed"""
    try:
        repair = Repair.query.get_or_404(repair_id)
        repair.status = 'completed'
        repair.completion_date = datetime.now().date()
        
        # Update instrument status if it was out of service
        if repair.instrument.status == 'repair':
            repair.instrument.status = 'active'
        
        db.session.commit()
        flash('Repair marked as completed!', 'success')
    except Exception as e:
        logging.error(f"Complete repair error: {e}")
        flash(f'Error completing repair: {str(e)}', 'danger')
    
    return redirect(url_for('repairs'))

@app.route('/departments')
@admin_required
def departments():
    """Show all departments (admin only)"""
    try:
        departments_list = Department.query.order_by(Department.name).all()
        return render_template('departments.html', departments=departments_list)
    except Exception as e:
        logging.error(f"Departments page error: {e}")
        flash(f'Error loading departments: {str(e)}', 'danger')
        return render_template('departments.html', departments=[])

@app.route('/add_department', methods=['POST'])
@admin_required
def add_department():
    """Add new department"""
    try:
        dept = Department()
        dept.name = request.form.get('name')
        dept.description = request.form.get('description')
        dept.manager_email = request.form.get('manager_email')
        
        db.session.add(dept)
        db.session.commit()
        
        flash('Department added successfully!', 'success')
    except Exception as e:
        logging.error(f"Add department error: {e}")
        flash(f'Error adding department: {str(e)}', 'danger')
    
    return redirect(url_for('departments'))

@app.route('/edit_department', methods=['POST'])
@admin_required
def edit_department():
    """Edit existing department"""
    try:
        dept_id = request.form.get('dept_id')
        dept = Department.query.get_or_404(dept_id)
        
        dept.name = request.form.get('name')
        dept.description = request.form.get('description')
        dept.manager_email = request.form.get('manager_email')
        
        db.session.commit()
        flash('Department updated successfully!', 'success')
    except Exception as e:
        logging.error(f"Edit department error: {e}")
        flash(f'Error updating department: {str(e)}', 'danger')
    
    return redirect(url_for('departments'))

@app.route('/delete_department', methods=['POST'])
@admin_required
def delete_department():
    """Delete department"""
    try:
        dept_id = request.form.get('dept_id')
        dept = Department.query.get_or_404(dept_id)
        
        # Unassign instruments from this department
        instruments = Instrument.query.filter_by(department_id=dept_id).all()
        for instrument in instruments:
            instrument.department_id = None
        
        db.session.delete(dept)
        db.session.commit()
        flash('Department deleted successfully!', 'success')
    except Exception as e:
        logging.error(f"Delete department error: {e}")
        flash(f'Error deleting department: {str(e)}', 'danger')
    
    return redirect(url_for('departments'))

@app.route('/send_reminders')
@admin_required 
def send_reminders():
    """Send email reminders for upcoming calibrations"""
    try:
        # Get instruments due for calibration in next 30 days
        from datetime import timedelta
        thirty_days = datetime.now().date() + timedelta(days=30)
        
        instruments = Instrument.query.all()
        reminders_sent = 0
        
        for instrument in instruments:
            status, days = calculate_calibration_status(
                instrument.last_calibration_date, 
                instrument.calibration_frequency
            )
            
            if status in ['upcoming', 'overdue']:
                # Get department manager email
                if instrument.department and instrument.department.manager_email:
                    subject = f"Calibration Reminder: {instrument.name}"
                    content = f"""
                    <h3>Calibration Reminder</h3>
                    <p>The following instrument requires calibration:</p>
                    <ul>
                        <li><strong>Instrument:</strong> {instrument.name}</li>
                        <li><strong>Manufacturer:</strong> {instrument.manufacturer}</li>
                        <li><strong>Last Calibration:</strong> {instrument.last_calibration_date}</li>
                        <li><strong>Status:</strong> {status.title()}</li>
                        <li><strong>Days:</strong> {days}</li>
                    </ul>
                    <p>Please schedule calibration as soon as possible.</p>
                    """
                    
                    if send_email_reminder(
                        instrument.department.manager_email,
                        subject,
                        content,
                        instrument.name
                    ):
                        # Create reminder record
                        reminder = Reminder()
                        reminder.instrument_id = instrument.id
                        reminder.reminder_date = datetime.now().date()
                        reminder.email_sent = True
                        reminder.sent_date = datetime.now()
                        db.session.add(reminder)
                        reminders_sent += 1
        
        db.session.commit()
        flash(f'Successfully sent {reminders_sent} email reminders!', 'success')
        
    except Exception as e:
        logging.error(f"Send reminders error: {e}")
        flash(f'Error sending reminders: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/reports')
@login_required
def reports():
    """
    Show calibration reports.

    NOTE: If you add, edit, or delete instruments, the report will update automatically
    as long as you reload the report page, because it queries the latest data from the database.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM instruments 
                ORDER BY last_calibration_date ASC
            ''')
            instruments = cursor.fetchall()
            
            # Process instruments for report
            report_data = []
            for instrument in instruments:
                status, days = calculate_calibration_status(
                    instrument['last_calibration_date'], 
                    instrument['calibration_frequency']
                )
                
                last_date = datetime.strptime(instrument['last_calibration_date'], '%Y-%m-%d')
                next_date = last_date + timedelta(days=instrument['calibration_frequency'])
                
                instrument_dict = dict(instrument)
                instrument_dict['status'] = status
                instrument_dict['days_info'] = days
                instrument_dict['next_calibration_date'] = next_date.strftime('%Y-%m-%d')
                report_data.append(instrument_dict)
            
            return render_template('reports.html', instruments=report_data)
            
    except Exception as e:
        logging.error(f"Reports error: {e}")
        flash(f'Error generating reports: {str(e)}', 'danger')
        return render_template('reports.html', instruments=[])
