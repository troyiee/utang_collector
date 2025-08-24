from flask import Flask, render_template, request, jsonify, session, redirect, url_for, g
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date
import re
import random
import string
import requests
from datetime import datetime, timedelta
import json
from functools import wraps
import os
from dotenv import load_dotenv
from threading import Thread
import time
import sqlite3


# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback-secret-key')

# SQLite configuration
DATABASE = os.getenv('DATABASE', 'debt_collection.db')

# Brevo API configuration
BREVO_API_KEY = os.getenv('BREVO_API_KEY')
BREVO_API_URL = 'https://api.brevo.com/v3/smtp/email'

@app.route("/")
def home():
    return "Hello, Render is working!"

def get_db():
    """Get database connection"""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row  # This enables column access by name
    return g.db

def close_db(e=None):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize the database with required tables"""
    db = get_db()
    
    # Create admins table
    db.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create clients table
    db.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            products TEXT NOT NULL,
            total_amount REAL NOT NULL,
            remaining_balance REAL NOT NULL,
            due_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES admins (id) ON DELETE CASCADE
        )
    ''')
    
    # Create SMS reminders table
    db.execute('''
        CREATE TABLE IF NOT EXISTS sms_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            method TEXT NOT NULL DEFAULT 'email_gateway',
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id) ON DELETE CASCADE
        )
    ''')
    
    db.commit()

@app.before_request
def before_request():
    """Initialize database connection before each request"""
    get_db()

@app.teardown_appcontext
def close_db_connection(exception):
    """Close database connection after each request"""
    close_db()

@app.context_processor
def inject_date():
    return {'date': date}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_email_brevo(to_email, subject, html_content):
    """Send email using Brevo API - optimized for SMS gateways"""
    if not BREVO_API_KEY:
        print("ERROR: BREVO_API_KEY is not set!")
        return False
    
    print(f"Attempting to send email to: {to_email}")
    
    headers = {
        'accept': 'application/json',
        'api-key': BREVO_API_KEY,
        'content-type': 'application/json'
    }
    
    # For SMS gateways, use plain text and minimal formatting
    is_sms_gateway = any(domain in to_email.lower() for domain in ['sms.', '.sms.', 'txt.', 'sun.com.ph'])
    
    data = {
        'sender': {
            'name': 'DebtReminder' if is_sms_gateway else 'Debt Collection System',
            'email': 'garciaraffitroy08@gmail.com'
        },
        'to': [{'email': to_email}],
        'subject': subject or ('Payment Reminder' if is_sms_gateway else 'Debt Collection System'),
        'htmlContent': html_content if not is_sms_gateway else html_content,
        'textContent': html_content if is_sms_gateway else None
    }
    
    # For SMS gateways, also add textContent
    if is_sms_gateway:
        data['textContent'] = html_content.replace('<br>', '\n').replace('<BR>', '\n')
    
    try:
        print("Sending request to Brevo API...")
        print(f"Request data: {data}")
        
        response = requests.post(BREVO_API_URL, headers=headers, json=data)
        print(f"Email API response status: {response.status_code}")
        print(f"Email API response body: {response.text}")
        
        if response.status_code == 201:
            print("Email sent successfully!")
            return True
        else:
            print(f"Email sending failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"Email error: {e}")
        return False
    
# Improved phone number validation function
def validate_phone_number(phone):
    """Validate Philippine mobile phone numbers"""
    if not phone:
        return False
    
    # Remove all non-digits
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    # Check if it's a valid Philippine mobile number
    # Format: 09xxxxxxxxx (11 digits) or 639xxxxxxxxx (12 digits) or 9xxxxxxxxx (10 digits)
    if len(clean_phone) == 11 and clean_phone.startswith('09'):
        return True
    elif len(clean_phone) == 12 and clean_phone.startswith('639'):
        return True
    elif len(clean_phone) == 10 and clean_phone.startswith('9'):
        return True
    
    return False
    
def send_sms_via_email_gateway(phone, message, carrier):
    """
    Send SMS via email-to-SMS gateway for Philippine carriers.
    """
    # Clean phone number to digits only
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    # Normalize to proper format
    if len(clean_phone) == 11 and clean_phone.startswith('09'):
        local_number = clean_phone[1:]  # Remove leading 0 -> 9xxxxxxxxx
    elif len(clean_phone) == 12 and clean_phone.startswith('639'):
        local_number = clean_phone[2:]  # Remove leading 63 -> 9xxxxxxxxx
    elif len(clean_phone) == 10 and clean_phone.startswith('9'):
        local_number = clean_phone  # Already correct -> 9xxxxxxxxx
    else:
        print(f"Invalid phone number format: {phone}")
        return False

    print(f"Formatted phone number: {local_number}")

    # Updated carrier email gateway mapping
    carrier_gateways = {
        'smart': f'{local_number}@sms.smart.com.ph',
        'globe': f'{local_number}@sms.globe.com.ph',
        'sun': f'{local_number}@sun.com.ph',
        # Alternative gateways to try
        'smart_alt': f'{local_number}@txt.smart.com.ph',
        'globe_alt': f'{local_number}@myglobe.sms.ph'
    }

    # Try primary gateway first
    if carrier not in carrier_gateways:
        print(f"Unknown carrier: {carrier}")
        return False

    to_email = carrier_gateways[carrier]
    print(f"Sending SMS via email gateway: {to_email}")

    # Keep SMS message short (160 characters max)
    if len(message) > 160:
        message = message[:157] + "..."
    
    # Simple text subject and content for SMS gateways
    subject = ""  # Some SMS gateways work better with empty subject
    html_content = message  # Plain text, no HTML formatting

    print(f"SMS Content: {message}")

    # Try sending via primary gateway
    success = send_email_brevo(to_email, subject, html_content)
    
    if not success and carrier in ['smart', 'globe']:
        # Try alternative gateway
        alt_carrier = f"{carrier}_alt"
        if alt_carrier in carrier_gateways:
            print(f"Trying alternative gateway: {carrier_gateways[alt_carrier]}")
            success = send_email_brevo(carrier_gateways[alt_carrier], subject, html_content)
    
    return success

@app.route('/check_sms_eligible_clients', methods=['GET'])
@login_required
def check_sms_eligible_clients():
    """Check how many clients are eligible for SMS reminders"""
    try:
        db = get_db()
        cursor = db.execute('''
            SELECT COUNT(*) as count FROM clients 
            WHERE admin_id = ? 
            AND phone IS NOT NULL 
            AND phone != '' 
            AND remaining_balance > 0
        ''', (session['admin_id'],))
        
        result = cursor.fetchone()
        count = result['count'] if result else 0
        
        return jsonify({
            'success': True, 
            'count': count,
            'message': f'Found {count} clients eligible for SMS reminders'
        })
        
    except Exception as e:
        print(f"Error checking SMS eligible clients: {e}")
        return jsonify({
            'success': False, 
            'count': 0,
            'message': 'Error checking eligible clients'
        })
        
# Replace the detect_carrier function
def detect_carrier(phone):
    clean = ''.join(filter(str.isdigit, phone))
    
    # Normalize to 11-digit format starting with 09
    if clean.startswith("639"):
        clean = "0" + clean[2:]
    elif clean.startswith("9") and len(clean) == 10:
        clean = "0" + clean
    elif len(clean) == 11 and clean.startswith("09"):
        pass  # Already correct format
    else:
        return None

    if len(clean) != 11 or not clean.startswith("09"):
        return None

    # Get first 4 digits for prefix matching
    prefix = clean[:4]
    
    # Updated prefix mappings for Philippine carriers
    smart_prefixes = {
        "0907", "0908", "0909", "0910", "0912", "0918", "0919", "0920", 
        "0921", "0928", "0929", "0939", "0998", "0999", "0947", "0949",
        "0998", "0999", "0813", "0947", "0994", "0992", "0993"
    }
    
    globe_prefixes = {
        "0905", "0906", "0915", "0916", "0917", "0926", "0927", "0935", 
        "0936", "0937", "0945", "0953", "0954", "0955", "0956", "0965", 
        "0966", "0967", "0975", "0976", "0977", "0995", "0996", "0997"
    }
    
    sun_prefixes = {
        "0922", "0923", "0924", "0925", "0931", "0932", "0933", "0934", 
        "0940", "0941", "0942", "0943", "0944", "0973", "0974"
    }

    if prefix in smart_prefixes:
        return "smart"
    elif prefix in globe_prefixes:
        return "globe"
    elif prefix in sun_prefixes:
        return "sun"
    else:
        # For 0932 prefix (your number), it should be Globe
        print(f"Unknown prefix: {prefix}, defaulting to Globe")
        return "globe"
    
#endpoint to get fully paid clients for recent activity
@app.route('/get_recent_paid_clients')
@login_required
def get_recent_paid_clients():
    try:
        db = get_db()
        cursor = db.execute('''
            SELECT * FROM clients 
            WHERE admin_id = ? AND remaining_balance <= 0 
            ORDER BY created_at DESC 
            LIMIT 5
        ''', (session['admin_id'],))
        
        recent_paid = cursor.fetchall()
        
        # Format the data
        formatted_clients = []
        for client in recent_paid:
            formatted_clients.append({
                'id': client['id'],
                'name': client['name'],
                'phone': client['phone'] or 'N/A',
                'total_amount': float(client['total_amount']),
                'products': client['products'],
                'due_date': client['due_date'] if client['due_date'] else 'N/A',
                'created_at': client['created_at'] if client['created_at'] else 'N/A'
            })
        
        return jsonify({
            'success': True,
            'clients': formatted_clients
        })
        
    except Exception as e:
        print(f"Get recent paid clients error: {e}")
        return jsonify({
            'success': False,
            'clients': []
        })
        
# SMS Gateway via Email (Completely FREE) - SINGLE DEFINITION
@app.route('/send_sms_reminder/<int:client_id>', methods=['POST'])
@login_required
def send_sms_reminder(client_id):
    try:
        db = get_db()
        cursor = db.execute('SELECT * FROM clients WHERE id = ? AND admin_id = ?', (client_id, session['admin_id']))
        client = cursor.fetchone()
        
        print(f"=== SMS DEBUG: Client lookup for ID {client_id} ===")
        
        if not client:
            print(f"ERROR: Client {client_id} not found for admin {session['admin_id']}")
            return jsonify({'success': False, 'message': 'Client not found'})
        
        print(f"Client found: {client['name']}, Phone: {client['phone']}")
        
        if not client['phone'] or client['phone'].strip() == '':
            print(f"ERROR: Client {client['name']} has no phone number")
            return jsonify({'success': False, 'message': f"Client {client['name']} has no phone number"})
        
        # Validate phone number
        if not validate_phone_number(client['phone']):
            print(f"ERROR: Invalid phone number format: {client['phone']}")
            return jsonify({'success': False, 'message': f'Invalid phone number format: {client["phone"]}'})
        
        print(f"Phone number validated: {client['phone']}")
        
        # Create shorter SMS message (SMS has 160 char limit)
        message = f"PAYMENT REMINDER: Hi {client['name']}, Amount Due: PHP{client['remaining_balance']:,.2f}. Please settle ASAP. Thank you!"
        
        # Ensure message is under 160 characters
        if len(message) > 160:
            message = f"PAYMENT DUE: {client['name']}, PHP{client['remaining_balance']:,.2f}. Please settle ASAP."
        
        print(f"SMS Message: {message} (Length: {len(message)})")
        
        # Detect carrier
        carrier = detect_carrier(client['phone'])
        print(f"Detected carrier: {carrier}")
        
        sms_sent = False
        
        if carrier:
            print(f"Trying detected carrier: {carrier}")
            if send_sms_via_email_gateway(client['phone'], message, carrier):
                sms_sent = True
                print(f"✓ SMS sent successfully via {carrier}")
        
        # If carrier detection failed or sending failed, try all carriers
        if not sms_sent:
            print("Trying all carriers...")
            carriers_to_try = ['globe', 'smart', 'sun']
            
            for test_carrier in carriers_to_try:
                print(f"Trying {test_carrier} gateway...")
                try:
                    if send_sms_via_email_gateway(client['phone'], message, test_carrier):
                        sms_sent = True
                        print(f"✓ SMS sent successfully via {test_carrier}")
                        break
                    else:
                        print(f"✗ Failed via {test_carrier}")
                except Exception as carrier_error:
                    print(f"✗ Error with {test_carrier}: {str(carrier_error)}")
        
        if sms_sent:
            # Log the SMS reminder
            try:
                db.execute('INSERT INTO sms_reminders (client_id, method, sent_at) VALUES (?, ?, ?)', 
                          (client['id'], 'email_gateway', datetime.now().isoformat()))
                db.commit()
                print(f"✓ SMS reminder logged successfully")
            except Exception as log_error:
                print(f"Warning: Failed to log SMS reminder: {log_error}")
            
            return jsonify({
                'success': True, 
                'message': f'FREE SMS reminder sent to {client["name"]} at {client["phone"]}!'
            })
        else:
            print(f"✗ All SMS attempts failed")
            return jsonify({
                'success': False, 
                'message': f'Failed to send SMS to {client["phone"]}. The SMS gateway may be temporarily unavailable.'
            })
            
    except Exception as e:
        print(f"SMS reminder error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Failed to send SMS reminder: {str(e)}'})

@app.route('/send_all_sms_reminders', methods=['POST'])
@login_required
def send_all_sms_reminders():
    """Send SMS reminders to all clients with outstanding balances and phone numbers"""
    try:
        db = get_db()
        cursor = db.execute('''
            SELECT * FROM clients 
            WHERE admin_id = ? 
            AND phone IS NOT NULL 
            AND phone != '' 
            AND remaining_balance > 0
        ''', (session['admin_id'],))
        
        eligible_clients = cursor.fetchall()
        
        if not eligible_clients:
            return jsonify({
                'success': False, 
                'message': 'No clients with phone numbers and outstanding balances found'
            })
        
        sent_count = 0
        failed_count = 0
        
        for client in eligible_clients:
            # Validate phone number
            if not validate_phone_number(client['phone']):
                failed_count += 1
                continue
            
            # Calculate days overdue/due
            today = date.today()
            days_diff = None
            if client['due_date']:
                try:
                    client_due_date = datetime.strptime(client['due_date'], '%Y-%m-%d').date()
                    days_diff = (client_due_date - today).days
                except ValueError:
                    pass
            
            # Create SMS message
            if days_diff is not None:
                if days_diff < 0:
                    urgency = f"OVERDUE by {abs(days_diff)} days"
                elif days_diff == 0:
                    urgency = "DUE TODAY"
                elif days_diff <= 3:
                    urgency = f"Due in {days_diff} day(s)"
                else:
                    urgency = f"Due: {client['due_date']}"
            else:
                urgency = "Payment Due"
            
            message = f"""PAYMENT REMINDER
Hi {client['name']},
{urgency}
Amount: PHP{client['remaining_balance']:,.2f}
Please settle ASAP. Thank you!"""
            
            # Try sending SMS
            sms_sent = False
            
            # First try to detect carrier
            carrier = detect_carrier(client['phone'])
            if carrier:
                if send_sms_via_email_gateway(client['phone'], message, carrier):
                    sms_sent = True
            
            # If detection failed, try all carriers
            if not sms_sent:
                carriers = ['smart', 'sun', 'tm']
                for carrier in carriers:
                    if send_sms_via_email_gateway(client['phone'], message, carrier):
                        sms_sent = True
                        break
            
            if sms_sent:
                sent_count += 1
                # Log the SMS reminder
                try:
                    db.execute('INSERT INTO sms_reminders (client_id, method, sent_at) VALUES (?, ?, ?)', 
                              (client['id'], 'email_gateway', datetime.now().isoformat()))
                    db.commit()
                except Exception as log_error:
                    print(f"Warning: Failed to log SMS reminder: {log_error}")
            else:
                failed_count += 1
        
        return jsonify({
            'success': True if sent_count > 0 else False,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'message': f'Sent {sent_count} SMS reminders, {failed_count} failed'
        })
        
    except Exception as e:
        print(f"Send all SMS reminders error: {e}")
        return jsonify({
            'success': False, 
            'message': f'Failed to send SMS reminders: {str(e)}'
        })

@app.route('/')
def index():
    if 'admin_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            data = request.get_json()
            username = data['username']
            email = data['email']
            password = data['password']
            
            db = get_db()
            cursor = db.execute('SELECT * FROM admins WHERE email = ?', (email,))
            account = cursor.fetchone()
            
            if account:
                return jsonify({'success': False, 'message': 'Email already exists!'})
            elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
                return jsonify({'success': False, 'message': 'Invalid email address!'})
            elif not username or not password or not email:
                return jsonify({'success': False, 'message': 'Please fill out the form!'})
            else:
                otp = generate_otp()
                hashed_password = generate_password_hash(password)
                
                # Store temporary registration data
                session['temp_registration'] = {
                    'username': username,
                    'email': email,
                    'password': hashed_password,
                    'otp': otp
                }
                
                # Send OTP email
                html_content = f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; font-family: Arial, sans-serif;">
                    <div style="background: white; border-radius: 15px; padding: 30px; max-width: 500px; margin: 0 auto; box-shadow: 0 20px 40px rgba(0,0,0,0.1);">
                        <h2 style="color: #667eea; text-align: center; margin-bottom: 30px;">Debt Collection System</h2>
                        <h3 style="color: #333; text-align: center;">Email Verification</h3>
                        <p style="color: #666; text-align: center; margin-bottom: 30px;">Your OTP verification code is:</p>
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-size: 32px; font-weight: bold; text-align: center; padding: 20px; border-radius: 10px; letter-spacing: 5px;">
                            {otp}
                        </div>
                        <p style="color: #999; text-align: center; margin-top: 20px; font-size: 14px;">This code will expire in 10 minutes.</p>
                    </div>
                </div>
                """
                
                if send_email_brevo(email, 'Email Verification - Debt Collection System', html_content):
                    return jsonify({'success': True, 'message': 'OTP sent to your email! Please check your inbox.'})
                else:
                    return jsonify({'success': False, 'message': 'Failed to send OTP email!'})
        except Exception as e:
            print(f"Registration error: {e}")
            return jsonify({'success': False, 'message': 'Registration failed!'})
    
    return render_template('register.html')

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json()
        otp = data['otp']
        
        if 'temp_registration' not in session:
            return jsonify({'success': False, 'message': 'Registration session expired!'})
        
        temp_data = session['temp_registration']
        
        if otp == temp_data['otp']:
            # Create account
            db = get_db()
            db.execute('INSERT INTO admins (username, email, password) VALUES (?, ?, ?)', 
                      (temp_data['username'], temp_data['email'], temp_data['password']))
            db.commit()
            
            # Clean up session
            session.pop('temp_registration', None)
            
            return jsonify({'success': True, 'message': 'Account created successfully!'})
        else:
            return jsonify({'success': False, 'message': 'Invalid OTP!'})
    except Exception as e:
        print(f"OTP verification error: {e}")
        return jsonify({'success': False, 'message': 'Verification failed!'})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            data = request.get_json()
            email = data['email']
            password = data['password']
            
            db = get_db()
            cursor = db.execute('SELECT * FROM admins WHERE email = ?', (email,))
            account = cursor.fetchone()
            
            if account and check_password_hash(account['password'], password):
                session['admin_id'] = account['id']
                session['username'] = account['username']
                return jsonify({'success': True, 'message': 'Login successful!'})
            else:
                return jsonify({'success': False, 'message': 'Invalid email or password!'})
        except Exception as e:
            print(f"Login error: {e}")
            return jsonify({'success': False, 'message': 'Login failed!'})
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        db = get_db()
        
        # Get statistics
        cursor = db.execute('SELECT COUNT(*) as total_clients FROM clients WHERE admin_id = ?', (session['admin_id'],))
        total_clients = cursor.fetchone()['total_clients']
        
        cursor = db.execute('SELECT SUM(total_amount) as total_debt FROM clients WHERE admin_id = ?', (session['admin_id'],))
        result = cursor.fetchone()
        total_debt = result['total_debt'] if result['total_debt'] else 0
        
        cursor = db.execute('SELECT SUM(remaining_balance) as total_outstanding FROM clients WHERE admin_id = ?', (session['admin_id'],))
        result = cursor.fetchone()
        total_outstanding = result['total_outstanding'] if result['total_outstanding'] else 0
        
        # Get all clients for chart calculation
        cursor = db.execute('SELECT * FROM clients WHERE admin_id = ?', (session['admin_id'],))
        all_clients = cursor.fetchall()
        
        # Calculate chart data
        today = datetime.now().date()
        paid_count = 0
        pending_count = 0
        overdue_count = 0

        for client in all_clients:
            if client['remaining_balance'] <= 0:
                paid_count += 1
            elif client['due_date']:
                try:
                    client_due_date = datetime.strptime(client['due_date'], '%Y-%m-%d').date()
                    days_diff = (client_due_date - today).days
                    if days_diff < 0:
                        overdue_count += 1
                    else:
                        pending_count += 1
                except ValueError:
                    if client['remaining_balance'] > 0:
                        pending_count += 1
                    else:
                        paid_count += 1
            else:
                # No due date but has remaining balance
                if client['remaining_balance'] > 0:
                    pending_count += 1
                else:
                    paid_count += 1

        # Calculate percentages for chart
        if total_clients > 0:
            paid_percentage = round((paid_count / total_clients) * 100, 1)
            pending_percentage = round((pending_count / total_clients) * 100, 1)
            overdue_percentage = round((overdue_count / total_clients) * 100, 1)
            
            # Adjust for rounding errors to ensure total is 100%
            total_percentage = paid_percentage + pending_percentage + overdue_percentage
            if total_percentage != 100:
                # Add the difference to the largest percentage
                max_key = max([('paid', paid_percentage), ('pending', pending_percentage), ('overdue', overdue_percentage)], key=lambda x: x[1])[0]
                if max_key == 'paid':
                    paid_percentage += (100 - total_percentage)
                elif max_key == 'pending':
                    pending_percentage += (100 - total_percentage)
                else:
                    overdue_percentage += (100 - total_percentage)
        else:
            paid_percentage = pending_percentage = overdue_percentage = 0

        chart_data = {
            'paid': {'count': paid_count, 'percentage': int(paid_percentage)},
            'pending': {'count': pending_count, 'percentage': int(pending_percentage)},
            'overdue': {'count': overdue_count, 'percentage': int(overdue_percentage)}
        }
        
        # Get clients with due payments (today, yesterday, tomorrow)
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        cursor = db.execute('''
            SELECT * FROM clients 
            WHERE admin_id = ? AND due_date IN (?, ?, ?) AND remaining_balance > 0
            ORDER BY due_date
        ''', (session['admin_id'], yesterday.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'), tomorrow.strftime('%Y-%m-%d')))
        
        due_clients = cursor.fetchall()
        
        # Add status calculation for each due client
        for client in due_clients:
            if client['due_date']:
                try:
                    client_due_date = datetime.strptime(client['due_date'], '%Y-%m-%d').date()
                    days_diff = (client_due_date - today).days
                    
                    if days_diff < 0:
                        client = dict(client)
                        client['status'] = 'overdue'
                        client['status_text'] = 'Overdue'
                    elif days_diff == 0:
                        client = dict(client)
                        client['status'] = 'due_today'
                        client['status_text'] = 'Due Today'
                    else:
                        client = dict(client)
                        client['status'] = 'due_tomorrow'
                        client['status_text'] = 'Due Tomorrow'
                except ValueError:
                    client = dict(client)
                    client['status'] = 'pending'
                    client['status_text'] = 'Pending'
        
        stats = {
            'total_clients': total_clients,
            'total_debt': f"P{total_debt:,.2f}",
            'total_outstanding': f"P{total_outstanding:,.2f}",
            'due_clients': len(due_clients)
        }
        
        return render_template('dashboard.html', 
                             stats=stats, 
                             due_clients=due_clients, 
                             chart_data=chart_data,
                             username=session.get('username', 'User'))
    except Exception as e:
        print(f"Dashboard error: {e}")
        return render_template('dashboard.html', 
                             stats={'total_clients': 0, 'total_debt': 'P0.00', 
                                   'total_outstanding': 'P0.00', 'due_clients': 0}, 
                             due_clients=[], 
                             chart_data={
                                 'paid': {'count': 0, 'percentage': 0},
                                 'pending': {'count': 0, 'percentage': 0},
                                 'overdue': {'count': 0, 'percentage': 0}
                             },
                             username=session.get('username', 'User'))

@app.route('/clients')
@login_required
def clients():
    try:
        db = get_db()
        cursor = db.execute('SELECT * FROM clients WHERE admin_id = ? ORDER BY created_at DESC', (session['admin_id'],))
        clients = cursor.fetchall()
        
        # Add days_diff calculation for each client
        today = date.today()
        
        # Initialize counters for chart data
        paid_count = 0
        pending_count = 0
        overdue_count = 0
        
        clients_list = []
        for client in clients:
            client_dict = dict(client)
            if client['due_date']:
                try:
                    client_due_date = datetime.strptime(client['due_date'], '%Y-%m-%d').date()
                    client_dict['days_diff'] = (client_due_date - today).days
                except ValueError:
                    client_dict['days_diff'] = None
            else:
                client_dict['days_diff'] = None
            
            # Calculate chart data based on payment status
            if client['remaining_balance'] <= 0:
                paid_count += 1
            elif client_dict['days_diff'] is not None and client_dict['days_diff'] < 0:
                overdue_count += 1
            else:
                pending_count += 1
            
            clients_list.append(client_dict)
        
        # Calculate percentages for chart
        total_clients = len(clients)
        if total_clients > 0:
            paid_percentage = round((paid_count / total_clients) * 100)
            pending_percentage = round((pending_count / total_clients) * 100)
            overdue_percentage = round((overdue_count / total_clients) * 100)
            
            # Ensure percentages add up to 100
            total_percentage = paid_percentage + pending_percentage + overdue_percentage
            if total_percentage != 100:
                paid_percentage += (100 - total_percentage)
        else:
            paid_percentage = pending_percentage = overdue_percentage = 0
        
        chart_data = {
            'paid': {'count': paid_count, 'percentage': paid_percentage},
            'pending': {'count': pending_count, 'percentage': pending_percentage},
            'overdue': {'count': overdue_count, 'percentage': overdue_percentage}
        }
        
        return render_template('clients.html', clients=clients_list, chart_data=chart_data)
    except Exception as e:
        print(f"Clients error: {e}")
        return render_template('clients.html', clients=[], chart_data={
            'paid': {'count': 0, 'percentage': 0},
            'pending': {'count': 0, 'percentage': 0},
            'overdue': {'count': 0, 'percentage': 0}
        })

# Mark as paid endpoint
@app.route('/mark_as_paid/<int:client_id>', methods=['PUT'])
@login_required
def mark_as_paid(client_id):
    try:
        db = get_db()
        db.execute('''
            UPDATE clients 
            SET remaining_balance = 0
            WHERE id = ? AND admin_id = ?
        ''', (client_id, session['admin_id']))
        db.commit()
        
        return jsonify({'success': True, 'message': 'Client marked as fully paid!'})
    except Exception as e:
        print(f"Mark as paid error: {e}")
        return jsonify({'success': False, 'message': 'Failed to mark client as paid!'})

@app.route('/add_client', methods=['POST'])
@login_required
def add_client():
    try:
        data = request.get_json()
        
        db = get_db()
        db.execute('''
            INSERT INTO clients (admin_id, name, phone, products, total_amount, remaining_balance, due_date) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            session['admin_id'],
            data['name'],
            data['phone'],
            data['products'],
            data['total_amount'],
            data['remaining_balance'],
            data['due_date']
        ))
        db.commit()
        
        return jsonify({'success': True, 'message': 'Client added successfully!'})
    except Exception as e:
        print(f"Add client error: {e}")
        return jsonify({'success': False, 'message': 'Failed to add client!'})

@app.route('/update_client/<int:client_id>', methods=['PUT'])
@login_required
def update_client(client_id):
    try:
        data = request.get_json()
        
        db = get_db()
        db.execute('''
            UPDATE clients 
            SET name = ?, phone = ?, products = ?, 
                total_amount = ?, remaining_balance = ?, due_date = ?
            WHERE id = ? AND admin_id = ?
        ''', (
            data['name'],
            data['phone'],
            data['products'],
            data['total_amount'],
            data['remaining_balance'],
            data['due_date'],
            client_id,
            session['admin_id']
        ))
        db.commit()
        
        return jsonify({'success': True, 'message': 'Client updated successfully!'})
    except Exception as e:
        print(f"Update client error: {e}")
        return jsonify({'success': False, 'message': 'Failed to update client!'})

@app.route('/delete_client/<int:client_id>', methods=['DELETE'])
@login_required
def delete_client(client_id):
    try:
        db = get_db()
        db.execute('DELETE FROM clients WHERE id = ? AND admin_id = ?', (client_id, session['admin_id']))
        db.commit()
        
        return jsonify({'success': True, 'message': 'Client deleted successfully!'})
    except Exception as e:
        print(f"Delete client error: {e}")
        return jsonify({'success': False, 'message': 'Failed to delete client!'})

@app.route('/send_reminder/<int:client_id>', methods=['POST'])
@login_required
def send_reminder(client_id):
    try:
        db = get_db()
        cursor = db.execute('SELECT * FROM clients WHERE id = ? AND admin_id = ?', (client_id, session['admin_id']))
        client = cursor.fetchone()
        
        if not client:
            return jsonify({'success': False, 'message': 'Client not found!'})
        
        # Get admin email for sending reminders
        cursor = db.execute('SELECT email FROM admins WHERE id = ?', (session['admin_id'],))
        admin = cursor.fetchone()
        admin_email = admin['email'] if admin else None
        
        if not admin_email:
            return jsonify({'success': False, 'message': 'Admin email not found!'})
        
        # Send reminder email to admin about the client
        html_content = f"""
        <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); padding: 30px; font-family: Arial, sans-serif;">
            <div style="background: white; border-radius: 15px; padding: 30px; max-width: 600px; margin: 0 auto; box-shadow: 0 20px 40px rgba(0,0,0,0.1);">
                <h2 style="color: #ff6b6b; text-align: center; margin-bottom: 30px;">Client Payment Reminder</h2>
                <p style="color: #333; font-size: 18px;">Client: {client['name']}</p>
                <p style="color: #666; line-height: 1.6;">Payment due date: <strong>{client['due_date']}</strong></p>
                <p style="color: #666; line-height: 1.6;">Phone: <strong>{client['phone'] or 'Not provided'}</strong></p>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <h3 style="color: #333; margin-top: 0;">Payment Details:</h3>
                    <p style="color: #666; margin: 10px 0;"><strong>Products:</strong> {client['products']}</p>
                    <p style="color: #666; margin: 10px 0;"><strong>Total Amount:</strong> PHP{client['total_amount']}</p>
                    <p style="color: #ff6b6b; margin: 10px 0; font-size: 20px;"><strong>Outstanding Balance: PHP{client['remaining_balance']}</strong></p>
                </div>
                
                <p style="color: #666; line-height: 1.6;">This is a reminder to follow up with the client for payment.</p>
            </div>
        </div>
        """
        
        if send_email_brevo(admin_email, f'Payment Reminder - {client["name"]}', html_content):
            return jsonify({'success': True, 'message': 'Reminder email sent to you successfully!'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send reminder email!'})
    except Exception as e:
        print(f"Send reminder error: {e}")
        return jsonify({'success': False, 'message': 'Failed to send reminder!'})

@app.route('/check_due_payments')
@login_required
def check_due_payments():
    try:
        db = get_db()
        
        # Get clients with payments due today, yesterday, or tomorrow
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        cursor = db.execute('''
            SELECT * FROM clients 
            WHERE admin_id = ? AND due_date IN (?, ?, ?) AND remaining_balance > 0
        ''', (session['admin_id'], yesterday.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'), tomorrow.strftime('%Y-%m-%d')))
        
        due_clients = cursor.fetchall()
        
        notifications = []
        for client in due_clients:
            try:
                client_due_date = datetime.strptime(client['due_date'], '%Y-%m-%d').date()
                if client_due_date == yesterday:
                    status = 'overdue'
                    message = f"{client['name']}'s payment was due yesterday (PHP{client['remaining_balance']})"
                elif client_due_date == today:
                    status = 'due_today'
                    message = f"{client['name']}'s payment is due today (PHP{client['remaining_balance']})"
                else:
                    status = 'due_tomorrow'
                    message = f"{client['name']}'s payment is due tomorrow (PHP{client['remaining_balance']})"
                
                notifications.append({
                    'client_id': client['id'],
                    'client_name': client['name'],
                    'amount': client['remaining_balance'],
                    'due_date': client['due_date'],
                    'status': status,
                    'message': message
                })
            except ValueError:
                continue
        
        return jsonify({'notifications': notifications})
    except Exception as e:
        print(f"Check due payments error: {e}")
        return jsonify({'notifications': []})

def run_payment_notifications():
    """Background task to automatically send payment notifications"""
    def should_send_notifications():
        """Check if current time matches notification schedule"""
        current_hour = datetime.now().hour
        return current_hour in [8, 14, 18]  # 8 AM, 2 PM, 6 PM
    
    def job():
        try:
            with app.app_context():
                db = get_db()
                cursor = db.execute('SELECT id, email FROM admins')
                admins = cursor.fetchall()
                
                for admin in admins:
                    notifications_sent = check_payment_status_for_admin(admin['id'], admin['email'])
                    if notifications_sent > 0:
                        print(f"✅ Sent {notifications_sent} automatic notifications to {admin['email']}")
        except Exception as e:
            print(f"❌ Automatic notification error: {e}")
    
    last_check_hour = -1
    print("🔄 Automatic notification system running...")
    
    while True:
        try:
            current_hour = datetime.now().hour
            
            # Only run once per hour at the scheduled times
            if should_send_notifications() and current_hour != last_check_hour:
                print(f"📧 Running automatic notification check at {datetime.now().strftime('%H:%M:%S')}")
                job()
                last_check_hour = current_hour
            
            # Check every 10 minutes
            time.sleep(600)
        except Exception as e:
            print(f"❌ Notification scheduler error: {e}")
            time.sleep(600)  # Continue running even if there's an error

def check_payment_status_for_admin(admin_id, admin_email):
    """Check payment status for specific admin and send notifications"""
    try:
        db = get_db()
        
        today = date.today()
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)
        
        # Get clients due today, tomorrow, or overdue for this admin
        cursor = db.execute('''
            SELECT * FROM clients 
            WHERE admin_id = ? 
            AND due_date IN (?, ?, ?) 
            AND remaining_balance > 0
        ''', (admin_id, yesterday.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'), tomorrow.strftime('%Y-%m-%d')))
        
        due_clients = cursor.fetchall()
        
        notifications_sent = 0
        for client in due_clients:
            if send_automatic_payment_notification(client, admin_email):
                notifications_sent += 1
                time.sleep(1)  # Small delay between emails
        
        return notifications_sent
    except Exception as e:
        print(f"❌ Payment status check error for admin {admin_id}: {e}")
        return 0

def send_automatic_payment_notification(client, admin_email):
    """Send automatic Gmail notification for client payment status"""
    try:
        today = date.today()
        try:
            client_due_date = datetime.strptime(client['due_date'], '%Y-%m-%d').date()
        except ValueError:
            return False
        
        days_diff = (client_due_date - today).days
        
        # Determine status and email content
        if days_diff < 0:
            status = "OVERDUE"
            urgency_color = "#f44336"
            status_icon = "⚠️"
            priority = "HIGH PRIORITY"
        elif days_diff == 0:
            status = "DUE TODAY"
            urgency_color = "#ff9800"
            status_icon = "🔔"
            priority = "URGENT"
        else:
            status = "DUE TOMORROW"
            urgency_color = "#2196f3"
            status_icon = "📅"
            priority = "REMINDER"
        
        html_content = f"""
        <div style="background: linear-gradient(135deg, {urgency_color} 0%, {urgency_color}dd 100%); padding: 30px; font-family: Arial, sans-serif;">
            <div style="background: white; border-radius: 15px; padding: 30px; max-width: 600px; margin: 0 auto; box-shadow: 0 20px 40px rgba(0,0,0,0.1);">
                <h2 style="color: {urgency_color}; text-align: center; margin-bottom: 10px;">{status_icon} AUTOMATIC PAYMENT ALERT</h2>
                <p style="text-align: center; background: {urgency_color}; color: white; padding: 8px 16px; border-radius: 20px; display: inline-block; font-weight: bold; font-size: 12px; margin-bottom: 20px;">{priority}</p>
                
                <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0; border-left: 5px solid {urgency_color};">
                    <h3 style="color: #333; margin-top: 0;">Client: {client['name']}</h3>
                    <p style="margin: 8px 0;"><strong>Phone:</strong> {client['phone'] or 'Not provided'}</p>
                    <p style="margin: 8px 0;"><strong>Products:</strong> {client['products']}</p>
                </div>
                
                <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <h3 style="color: #856404; margin-top: 0;">Payment Status: {status}</h3>
                    <p style="margin: 8px 0;"><strong>Due Date:</strong> {client['due_date']}</p>
                    <p style="margin: 8px 0;"><strong>Total Amount:</strong> PHP{client['total_amount']:,.2f}</p>
                    <p style="margin: 8px 0; font-size: 18px;"><strong style="color: {urgency_color};">Outstanding Balance: PHP{client['remaining_balance']:,.2f}</strong></p>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding: 15px; background: #e3f2fd; border-radius: 8px;">
                    <p style="color: #1976d2; margin: 0; font-size: 14px;">
                        <strong>⏰ Sent automatically at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong>
                    </p>
                    <p style="color: #666; margin: 5px 0 0 0; font-size: 12px;">
                        Debt Collection System - Automatic Notifications
                    </p>
                </div>
            </div>
        </div>
        """
        
        subject = f"[AUTO-ALERT] {status} - {client['name']} (PHP{client['remaining_balance']:,.2f})"
        
        success = send_email_brevo(admin_email, subject, html_content)
        if success:
            print(f"📧 Sent {status} notification for {client['name']} to {admin_email}")
        
        return success
        
    except Exception as e:
        print(f"❌ Send automatic notification error: {e}")
        return False

# Start automatic notification system
def start_notification_scheduler():
    """Start the background notification system"""
    try:
        notification_thread = Thread(target=run_payment_notifications, daemon=True)
        notification_thread.start()
        print("✅ Automatic payment notification system started!")
        print("📧 Will check and send notifications at 8:00 AM, 2:00 PM, and 6:00 PM daily")
        print("🔄 Notification system is now running in the background...")
    except Exception as e:
        print(f"❌ Failed to start notification system: {e}")

@app.route('/logout')
def logout():
    session.pop('admin_id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/get_notification_stats')
@login_required
def get_notification_stats():
    try:
        db = get_db()
        
        today = date.today()
        tomorrow = today + timedelta(days=1)
        week_ago = today - timedelta(days=7)
        
        # Count notifications for today
        cursor = db.execute('''
            SELECT COUNT(*) as count FROM clients 
            WHERE admin_id = ? AND due_date = ? AND remaining_balance > 0
        ''', (session['admin_id'], today.strftime('%Y-%m-%d')))
        due_today_count = cursor.fetchone()['count']
        
        cursor = db.execute('''
            SELECT COUNT(*) as count FROM clients 
            WHERE admin_id = ? AND due_date = ? AND remaining_balance > 0
        ''', (session['admin_id'], tomorrow.strftime('%Y-%m-%d')))
        due_tomorrow_count = cursor.fetchone()['count']
        
        cursor = db.execute('''
            SELECT COUNT(*) as count FROM clients 
            WHERE admin_id = ? AND due_date < ? AND remaining_balance > 0
        ''', (session['admin_id'], today.strftime('%Y-%m-%d')))
        overdue_count = cursor.fetchone()['count']
        
        # Count total notifications for this week
        cursor = db.execute('''
            SELECT COUNT(*) as count FROM clients 
            WHERE admin_id = ? AND due_date >= ? AND due_date <= ? AND remaining_balance > 0
        ''', (session['admin_id'], week_ago.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')))
        week_total = cursor.fetchone()['count']
        
        return jsonify({
            'success': True,
            'today': {
                'due_today': due_today_count,
                'due_tomorrow': due_tomorrow_count,
                'overdue': overdue_count
            },
            'week': {
                'total': week_total
            }
        })
        
    except Exception as e:
        print(f"Get notification stats error: {e}")
        return jsonify({
            'success': False, 
            'message': f'Error getting notification stats: {str(e)}'
        })

@app.route('/check_due_status_changes')
@login_required
def check_due_status_changes():
    try:
        db = get_db()
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        # Check for clients with status changes (this is a simplified version)
        cursor = db.execute('''
            SELECT COUNT(*) as count FROM clients 
            WHERE admin_id = ? AND due_date IN (?, ?, ?) AND remaining_balance > 0
        ''', (session['admin_id'], yesterday.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'), tomorrow.strftime('%Y-%m-%d')))
        
        current_notifications = cursor.fetchone()['count']
        
        # For real-time updates, you would compare with previous counts
        # For now, we'll just return the current status
        return jsonify({
            'success': True,
            'has_new_notifications': False,  # Set to True when you detect changes
            'notifications_sent': current_notifications
        })
        
    except Exception as e:
        print(f"Check due status changes error: {e}")
        return jsonify({
            'success': False,
            'has_new_notifications': False,
            'notifications_sent': 0
        })

# Initialize database on startup
with app.app_context():
    init_db()

# Initialize automatic notifications when app starts
try:
    start_notification_scheduler()
except Exception as e:
    print(f"Warning: Could not start automatic notifications: {e}")

if __name__ == '__main__':
    app.run(debug=True)