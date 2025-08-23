# Debt Collection System

A comprehensive web-based debt collection management system built with Flask that helps businesses track outstanding payments, send automated reminders, and manage client information efficiently.

## 🚀 Features

### Core Functionality
- **Client Management**: Add, edit, update, and delete client information
- **Payment Tracking**: Monitor total amounts, remaining balances, and payment history
- **Due Date Management**: Track payment due dates with automatic status updates
- **Dashboard Analytics**: Visual charts showing payment status distribution
- **Real-time Notifications**: Automatic email notifications for due/overdue payments

### Communication Features
- **Email Notifications**: Automated email reminders using Brevo API
- **SMS Reminders**: SMS notifications via email-to-SMS gateways for Philippine carriers (Smart, Globe, Sun)
- **OTP Verification**: Secure email-based OTP for user registration
- **Notification Logging**: Complete audit trail of all sent notifications

### Security & Authentication
- **User Registration**: Secure account creation with email verification
- **Session Management**: Protected routes with login requirements
- **Password Hashing**: Secure password storage using Werkzeug
- **Environment Variables**: Secure configuration management

## 🛠️ Technologies Used

- **Backend**: Flask (Python)
- **Database**: MySQL with Flask-MySQLdb
- **Email Service**: Brevo API (formerly SendinBlue)
- **Security**: Werkzeug password hashing
- **Frontend**: HTML, CSS, JavaScript (Bootstrap for styling)
- **Environment**: python-dotenv for configuration

## 📋 Prerequisites

- Python 3.7+
- MySQL 5.7+ or MySQL 8.0+
- SMTP email service (Brevo account recommended)

## ⚙️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd debt-collection-system
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install flask flask-mysqldb werkzeug requests python-dotenv
```

### 4. Database Setup

Create a MySQL database and the following tables:

```sql
-- Create database
CREATE DATABASE debt_collection;
USE debt_collection;

-- Admins table
CREATE TABLE admins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Clients table
CREATE TABLE clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    products TEXT,
    total_amount DECIMAL(10,2) NOT NULL,
    remaining_balance DECIMAL(10,2) NOT NULL,
    due_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
);

-- Notification log table
CREATE TABLE notification_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    sent_to_admin BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);

-- SMS reminders table
CREATE TABLE sms_reminders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    method VARCHAR(50) NOT NULL DEFAULT 'email_gateway',
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
);
```

### 5. Environment Configuration

Create a `.env` file in the root directory:

```env
# Flask Configuration
SECRET_KEY=your-super-secret-key-here

# MySQL Database Configuration
MYSQL_HOST=localhost
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DB=debt_collection
MYSQL_PORT=3306

# Optional: For managed MySQL (like PlanetScale)
# MYSQL_SSL_CA=/path/to/ca-certificate.crt

# Brevo API Configuration
BREVO_API_KEY=your-brevo-api-key-here
```

### 6. Get Brevo API Key

1. Sign up at [Brevo](https://www.brevo.com/) (formerly SendinBlue)
2. Go to SMTP & API > API Keys
3. Create a new API key
4. Add it to your `.env` file

## 🚀 Running the Application

### Development Mode
```bash
python app.py
```

The application will be available at `http://localhost:5000`

### Production Deployment

For production deployment, consider using:
- **Gunicorn** as WSGI server
- **Nginx** as reverse proxy
- **SSL certificate** for HTTPS
- **Environment-specific configurations**

Example with Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## 📱 SMS Configuration (Philippine Carriers)

The system supports SMS reminders via email-to-SMS gateways for Philippine mobile carriers:

### Supported Carriers
- **Smart**: `number@sms.smart.com.ph`, `number@txt.smart.com.ph`
- **Globe**: `number@sms.globe.com.ph`, `number@myglobe.sms.ph`
- **Sun**: `number@sun.com.ph`

### Phone Number Formats
The system accepts these Philippine mobile number formats:
- `09xxxxxxxxx` (11 digits)
- `639xxxxxxxxx` (12 digits)
- `9xxxxxxxxx` (10 digits)

## 📊 Usage Guide

### 1. Registration & Login
- Register with email verification (OTP-based)
- Login with email and password
- Secure session management

### 2. Client Management
- **Add Clients**: Include name, phone, products, amounts, and due dates
- **Update Information**: Edit client details as needed
- **Payment Tracking**: Monitor remaining balances
- **Status Indicators**: Visual indicators for paid/pending/overdue status

### 3. Notifications
- **Automatic Emails**: System sends notifications when payments become due/overdue
- **Manual SMS**: Send individual or bulk SMS reminders
- **Notification History**: View all sent notifications

### 4. Dashboard
- **Overview Statistics**: Total clients, debt amounts, outstanding balances
- **Visual Charts**: Payment status distribution
- **Due Payments**: Quick view of upcoming and overdue payments
- **Recent Activity**: Latest fully paid clients

## 🔧 API Endpoints

### Authentication
- `POST /register` - User registration
- `POST /verify_otp` - Email verification
- `POST /login` - User login
- `GET /logout` - User logout

### Client Management
- `GET /clients` - List all clients
- `POST /add_client` - Add new client
- `PUT /update_client/<id>` - Update client
- `DELETE /delete_client/<id>` - Delete client
- `PUT /mark_as_paid/<id>` - Mark client as fully paid

### Notifications
- `POST /send_sms_reminder/<id>` - Send SMS to specific client
- `POST /send_all_sms_reminders` - Send SMS to all eligible clients
- `GET /check_due_status_changes` - Check for status changes
- `GET /get_notification_stats` - Get notification statistics

### Dashboard
- `GET /dashboard` - Main dashboard
- `GET /check_due_payments` - Get due payments
- `GET /get_recent_paid_clients` - Get recently paid clients

## 🛡️ Security Features

- **Password Hashing**: All passwords are hashed using Werkzeug
- **Session Protection**: Login required decorators for protected routes
- **SQL Injection Prevention**: Parameterized queries throughout
- **Environment Variables**: Sensitive data stored in environment variables
- **Input Validation**: Phone number and email validation

## 🔄 Automatic Notifications

The system automatically sends email notifications for:
- **Due Today**: Payments due on the current day
- **Due Tomorrow**: Payments due the next day
- **Overdue**: Payments past their due date

Notifications include:
- Client information
- Payment details
- Urgency indicators
- Professional HTML formatting

## 📞 Support

For support with Philippine SMS gateways or general system issues:
- Check carrier-specific gateway documentation
- Verify phone number formats
- Monitor notification logs for delivery status
- Test with known working numbers first

## 🚨 Troubleshooting

### Common Issues

**SMS not sending:**
- Verify phone number format
- Check carrier detection
- Ensure Brevo API key is valid
- Test with different carriers

**Email notifications failing:**
- Verify Brevo API key
- Check internet connectivity
- Review API usage limits
- Validate email addresses

**Database connection errors:**
- Verify MySQL credentials
- Check database permissions
- Ensure database exists
- Test connection manually

**Session issues:**
- Check SECRET_KEY configuration
- Clear browser cookies
- Verify session timeout settings

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📧 Contact

For questions or support, please contact the development team or create an issue in the repository.

---

**Note**: This system is designed for Philippine mobile carriers and uses specific email-to-SMS gateways. For international use, modify the carrier detection and gateway configuration accordingly.#   d e b t _ c o l l e c t o r  
 