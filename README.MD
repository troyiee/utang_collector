# Debt Collection System

A comprehensive web application for managing debt collection, client tracking, and automated payment reminders built with Flask and SQLite.

## 🌐 Live Demo

**Try the application:** [https://utang-collector.onrender.com](https://utang-collector.onrender.com)

## 📋 Features

### Core Functionality
- **User Authentication**: Secure registration and login system with email verification
- **Client Management**: Add, edit, delete, and track client information
- **Payment Tracking**: Monitor total amounts, remaining balances, and due dates
- **Dashboard Analytics**: Visual charts showing payment status distribution
- **Due Date Monitoring**: Track overdue, due today, and upcoming payments

### Communication Features
- **Email Notifications**: Automated payment reminders via Brevo API
- **SMS Gateway**: Send SMS reminders through email-to-SMS gateways for Philippine carriers (Smart, Globe, Sun)
- **Bulk Notifications**: Send reminders to all eligible clients at once
- **Automatic Alerts**: Real-time notifications for payment status changes

### Analytics & Reporting
- **Payment Status Charts**: Visual representation of paid, pending, and overdue accounts
- **Recent Activity**: Track recently paid clients
- **Due Payment Alerts**: Instant notifications for payments due today, tomorrow, or overdue
- **Statistics Dashboard**: Overview of total clients, debt amounts, and outstanding balances

## 🛠️ Technology Stack

- **Backend**: Python Flask
- **Database**: SQLite
- **Frontend**: HTML, CSS, JavaScript (with Chart.js for analytics)
- **Email Service**: Brevo API
- **SMS**: Email-to-SMS gateway integration
- **Deployment**: Render

## 📦 Installation

### Prerequisites
- Python 3.7+
- pip package manager

### Setup Steps

1. **Clone the repository**
```bash
git clone <your-repository-url>
cd debt-collection-system
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install flask werkzeug python-dotenv requests
```

4. **Environment Configuration**
Create a `.env` file in the root directory:
```env
SECRET_KEY=your-secret-key-here
DATABASE=debt_collection.db
BREVO_API_KEY=your-brevo-api-key
```

5. **Initialize Database**
```bash
python app.py
```
The database will be automatically created on first run.

6. **Run the application**
```bash
python app.py
```
Access the application at `http://localhost:5000`

## 🔧 Configuration

### Email Setup (Brevo)
1. Sign up for a free Brevo account at [brevo.com](https://brevo.com)
2. Generate an API key from your account settings
3. Add the API key to your `.env` file as `BREVO_API_KEY`

### SMS Gateway Configuration
The system supports Philippine mobile carriers:
- **Smart**: Uses `@sms.smart.com.ph` and `@txt.smart.com.ph` gateways
- **Globe**: Uses `@sms.globe.com.ph` and `@myglobe.sms.ph` gateways  
- **Sun**: Uses `@sun.com.ph` gateway

SMS functionality works through email-to-SMS gateways and is completely free.

## 📱 Usage

### Getting Started
1. **Register**: Create an account with email verification
2. **Login**: Access your dashboard
3. **Add Clients**: Input client information, debt amounts, and due dates
4. **Monitor**: Use the dashboard to track payment statuses
5. **Send Reminders**: Use email or SMS reminders for overdue accounts

### Client Management
- Add new clients with contact information and payment details
- Edit existing client information and payment amounts
- Mark clients as fully paid when payments are received
- Delete clients when necessary

### Notification System
- **Manual Reminders**: Send individual email or SMS reminders
- **Bulk Notifications**: Send reminders to all eligible clients
- **Automatic Alerts**: Receive email notifications for status changes

## 📊 Dashboard Features

### Analytics Charts
- **Payment Status Distribution**: Pie chart showing paid, pending, and overdue percentages
- **Due Payments**: List of clients with payments due today, tomorrow, or overdue
- **Recent Activity**: Track recently paid clients

### Key Metrics
- Total number of clients
- Total debt amount
- Total outstanding balance
- Number of due payments

## 🔒 Security Features

- **Password Hashing**: Secure password storage using Werkzeug
- **Session Management**: Secure user sessions
- **Input Validation**: Phone number and email validation
- **SQL Injection Protection**: Parameterized queries
- **CSRF Protection**: Session-based security

## 📧 Notification System

### Email Notifications
- Beautiful HTML email templates
- Automatic payment alerts
- Status change notifications
- OTP verification emails

### SMS Integration
- Philippine carrier support (Smart, Globe, Sun)
- Automatic carrier detection
- 160-character message optimization
- Fallback carrier testing

## 🚀 Deployment

### Render Deployment
1. Connect your GitHub repository to Render
2. Set environment variables in Render dashboard
3. Deploy with automatic builds

### Environment Variables for Production
```env
SECRET_KEY=production-secret-key
DATABASE=debt_collection.db
BREVO_API_KEY=your-brevo-api-key
```

## 🛡️ Database Schema

### Tables
- **admins**: User accounts with authentication
- **clients**: Client information and debt details
- **sms_reminders**: SMS notification logs

### Relationships
- One admin can have many clients
- One client can have many SMS reminder logs

## 🔍 API Endpoints

### Authentication
- `POST /register` - User registration with email verification
- `POST /verify_otp` - Email verification
- `POST /login` - User login
- `GET /logout` - User logout

### Client Management
- `GET /clients` - View all clients
- `POST /add_client` - Add new client
- `PUT /update_client/<id>` - Update client information
- `DELETE /delete_client/<id>` - Delete client
- `PUT /mark_as_paid/<id>` - Mark client as fully paid

### Notifications
- `POST /send_reminder/<id>` - Send email reminder
- `POST /send_sms_reminder/<id>` - Send SMS reminder
- `POST /send_all_sms_reminders` - Send bulk SMS reminders

## 🔧 Troubleshooting

### Common Issues

**SMS Not Sending**
- Verify phone number format (Philippine numbers: 09XXXXXXXXX)
- Check carrier detection for Smart, Globe, or Sun
- Ensure Brevo API key is configured

**Email Notifications Failing**
- Verify Brevo API key is valid
- Check email format and sender configuration
- Monitor Brevo API response logs

**Database Issues**
- Ensure SQLite file permissions are correct
- Check database initialization on first run
- Verify foreign key constraints

## 📄 License

This project is open source and available under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For support or questions about this debt collection system, please create an issue in the repository or contact the development team.

## ⚡ Performance Notes

- **Database**: SQLite is suitable for small to medium-scale deployments
- **SMS Limits**: Email-to-SMS gateways may have carrier-specific limits
- **Email Limits**: Brevo free tier includes generous sending limits
- **Concurrent Users**: Flask development server is suitable for small teams

## 🔮 Future Enhancements

- Payment history tracking
- Advanced reporting and analytics
- Mobile app development
- Integration with payment processors
- Multi-language support
- Advanced SMS provider integration