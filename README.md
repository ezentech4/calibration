# Enhanced Calibration Manager

A comprehensive web application for managing instrument calibration schedules, repairs, and automated email reminders.

## Features

### Core Functionality
- **Instrument Management**: Add, edit, and track laboratory instruments
- **Calibration Scheduling**: Automatic calculation of calibration due dates
- **Status Tracking**: Real-time monitoring of calibration status (current, upcoming, overdue)
- **Reporting**: Export calibration reports and status summaries

### Enhanced Features
- **User Authentication**: Secure login system with password hashing
- **Department Management**: Organize instruments by departments
- **Repair Tracking**: Track equipment repairs and maintenance activities
- **Email Reminders**: Automated calibration notifications via SendGrid
- **Role-Based Access**: Admin and regular user permissions

## Installation

### Prerequisites
```bash
pip install Flask Flask-SQLAlchemy Flask-CORS Werkzeug psycopg2-binary sendgrid email-validator gunicorn
```

### Quick Start
1. Extract the zip file
2. Install dependencies: `pip install -r requirements.txt` (if available)
3. Set environment variables (optional):
   - `SESSION_SECRET`: Flask session secret
   - `DATABASE_URL`: PostgreSQL URL (defaults to SQLite)
   - `SENDGRID_API_KEY`: For email notifications
   - `FROM_EMAIL`: Email sender address
4. Run: `python app.py`
5. Access: http://localhost:5000

## Default Login
- Username: `admin`
- Password: `admin123`

## Database

The application supports both SQLite (default) and PostgreSQL databases. Tables are created automatically on first run.

### Database Schema
- **Users**: Authentication and user management
- **Departments**: Organizational units
- **Instruments**: Equipment tracking with calibration schedules
- **Repairs**: Maintenance and repair records
- **Reminders**: Email notification tracking

## Usage

### User Management
1. Login with admin account
2. Register new users through the registration page
3. Assign users to departments during registration

### Instrument Management
1. Add instruments with calibration frequency
2. Track calibration dates and status
3. Organize by departments
4. View dashboard for status overview

### Repair Tracking
1. Access "Repairs" section from navigation
2. Add repair records for instruments
3. Track repair progress and completion
4. Assign technicians and costs

### Email Reminders
1. Configure SendGrid API key in environment
2. Set department manager emails
3. Use "Send Reminders" feature to notify managers
4. Automatic tracking of sent notifications

## File Structure
```
calibration-manager/
├── app.py                 # Main application
├── main.py               # Application entry point
├── templates/            # HTML templates
│   ├── base.html        # Base template
│   ├── login.html       # Login page
│   ├── register.html    # Registration page
│   ├── dashboard.html   # Main dashboard
│   ├── instruments.html # Instrument listing
│   ├── add_instrument.html
│   ├── edit_instrument.html
│   ├── repairs.html     # Repair management
│   ├── add_repair.html  # Add repair form
│   └── reports.html     # Reports page
├── static/              # Static assets
│   ├── css/
│   │   └── custom.css   # Custom styling
│   └── js/
│       └── app.js       # JavaScript functionality
└── README.md           # This file
```

## Security Features
- Password hashing with Werkzeug
- Session management
- CSRF protection
- SQL injection prevention
- Role-based access control

## Contributing
This is a complete calibration management system ready for production use in laboratory and industrial environments.

## Project Description

Enhanced Calibration Manager is a web-based solution for laboratories and industrial facilities to manage instrument calibration, maintenance, and compliance. It streamlines scheduling, automates reminders, and provides robust reporting and access control.

## Screenshots

![Dashboard Screenshot](static/screenshots/dashboard.png)
![Instrument List](static/screenshots/instruments.png)

## Environment Variables

| Variable           | Description                       | Required | Default                |
|--------------------|-----------------------------------|----------|------------------------|
| SESSION_SECRET     | Flask session secret key          | Yes      | dev-secret-key         |
| DATABASE_URL       | SQLAlchemy DB URI (Postgres/SQLite)| No      | sqlite:///calibration.db|
| SENDGRID_API_KEY   | SendGrid API key for emails       | No       |                        |
| FROM_EMAIL         | Sender email address              | No       | calibration@company.com|

## Support

For issues or feature requests, please open an issue on GitHub or contact the maintainer at [your-email@example.com].

## License

This project is licensed under the MIT License.

## Testing

To run the test suite:
```bash
pytest tests/
```

## Deployment

For production, use a WSGI server such as Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

---

**You can copy and integrate these suggestions into your README for a more complete and professional documentation. If you want a full, revised README with these changes, let me know!**