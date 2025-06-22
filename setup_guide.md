# Calibration Manager Setup Guide

## Required Dependencies

To run the enhanced calibration manager locally, you need to install these Python packages:

### Install with pip:
```bash
pip install Flask==2.3.3
pip install Flask-SQLAlchemy==3.0.5
pip install Flask-CORS==4.0.0
pip install Werkzeug==2.3.7
pip install psycopg2-binary==2.9.7
pip install sendgrid==6.10.0
pip install email-validator==2.0.0
pip install gunicorn==21.2.0
```

### Or install all at once:
```bash
pip install Flask Flask-SQLAlchemy Flask-CORS Werkzeug psycopg2-binary sendgrid email-validator gunicorn
```

## Features Added

1. **User Authentication**: Login/logout system with password hashing
2. **Department Management**: Organize instruments by departments
3. **Repair Tracking**: Track equipment repairs and maintenance
4. **Email Reminders**: Send calibration notifications via SendGrid
5. **PostgreSQL Support**: Enhanced database with relationships

## Default Login
- Username: `admin`
- Password: `admin123`

## Environment Variables (Optional)
- `SESSION_SECRET`: Flask session secret key
- `DATABASE_URL`: PostgreSQL database URL (defaults to SQLite)
- `SENDGRID_API_KEY`: For email notifications
- `FROM_EMAIL`: Email sender address

## Running the Application
```bash
python app.py
```

The application will run on http://localhost:5000