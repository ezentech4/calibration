# Calibration Manager

## Overview

This is a Flask-based web application for managing calibration schedules and reminders for laboratory or industrial instruments. The system tracks instruments, their calibration dates, frequencies, and generates automated reminders for upcoming calibrations.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Flask
- **UI Framework**: Bootstrap 5 with dark theme optimized for Replit
- **JavaScript**: Vanilla JavaScript with modular approach
- **Styling**: Custom CSS extending Bootstrap with status indicators and animations

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Architecture Pattern**: Monolithic web application with MVC-like structure
- **Database ORM**: Raw SQLite3 with row factory for dictionary-like access
- **API Design**: RESTful endpoints with both HTML and JSON responses

### Data Storage
- **Primary Database**: SQLite3 (file-based database)
- **Database File**: `calibration.db` stored locally
- **Schema Design**: Two main tables - instruments and reminders with foreign key relationships

## Key Components

### Database Schema
- **Instruments Table**: Core entity storing instrument details, calibration history, and scheduling
  - Fields: id, name, serial_number, manufacturer, model, location, last_calibration_date, calibration_frequency, notes, timestamps
- **Reminders Table**: Tracks calibration reminders and their status
  - Fields: id, instrument_id (FK), reminder_date, status, created_at

### Core Features
- **Dashboard**: Overview with statistics and upcoming reminders
- **Instrument Management**: CRUD operations for instruments
- **Calibration Tracking**: Automatic calculation of due dates based on frequency
- **Reporting**: Export capabilities and detailed status reports
- **Status Classification**: Instruments categorized as current, upcoming, or overdue

### User Interface
- **Responsive Design**: Mobile-first Bootstrap layout
- **Dark Theme**: Replit-optimized dark theme for better developer experience
- **Interactive Elements**: Search, filtering, and sorting capabilities
- **Status Indicators**: Color-coded badges for calibration status

## Data Flow

1. **Instrument Registration**: Users add instruments with calibration details
2. **Automatic Scheduling**: System calculates next calibration dates based on frequency
3. **Status Monitoring**: Regular evaluation of calibration status (current/upcoming/overdue)
4. **Reminder Generation**: Automatic creation of reminder entries
5. **Reporting**: Generation of status reports and export functionality

## External Dependencies

### Python Packages
- **Flask**: Web framework and routing
- **Flask-CORS**: Cross-origin resource sharing support
- **Flask-SQLAlchemy**: Database ORM (prepared but not actively used)
- **Gunicorn**: Production WSGI server
- **psycopg2-binary**: PostgreSQL adapter (prepared for future migration)
- **email-validator**: Email validation utilities

### Frontend Dependencies
- **Bootstrap 5**: UI framework with Replit dark theme
- **Bootstrap Icons**: Icon library
- **Custom CSS**: Application-specific styling

### System Dependencies
- **SQLite3**: Database engine
- **Python 3.11**: Runtime environment
- **OpenSSL**: Security libraries
- **PostgreSQL**: Database server (prepared for future use)

## Deployment Strategy

### Development Environment
- **Runtime**: Python 3.11 on Nix stable-24_05
- **Local Server**: Flask development server with auto-reload
- **Database**: SQLite3 file-based storage

### Production Deployment
- **Server**: Gunicorn WSGI server
- **Scaling**: Autoscale deployment target on Replit
- **Port Configuration**: Application bound to 0.0.0.0:5000
- **Process Management**: Gunicorn with reuse-port and reload options

### Database Considerations
- **Current**: SQLite3 for simplicity and portability
- **Migration Path**: PostgreSQL adapter included for future scaling needs
- **Data Persistence**: Local file storage suitable for single-instance deployments

### Security Features
- **Session Management**: Flask secret key configuration
- **CORS**: Enabled for API access
- **Input Validation**: Form validation and SQL injection prevention through parameterized queries

The application follows a traditional web application pattern with server-side rendering, making it suitable for internal laboratory or facility management use cases where instrument calibration tracking is critical for compliance and quality assurance.