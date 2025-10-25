# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

NetAuto Platform is a Django-based network automation platform for Huawei and Cisco switches/routers using Python Netmiko for device automation. The project provides a web GUI for network device management and automation tasks.

**Tech Stack:**
- Backend: Django 5.2.7
- Network Automation: Netmiko (Cisco, Huawei support)
- Database: SQLite (development), configurable via django-environ
- Configuration Management: django-environ with .env files

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
copy .env.example .env
# Edit .env with your configuration
```

### Django Management
```bash
# Database operations
python manage.py migrate
python manage.py makemigrations
python manage.py createsuperuser

# Development server
python manage.py runserver

# Django shell
python manage.py shell

# Collect static files (if needed)
python manage.py collectstatic
```

### Testing
```bash
# Run all tests
python manage.py test

# Run tests for specific app
python manage.py test automation

# Run tests with verbose output
python manage.py test --verbosity=2
```

## Architecture

### Project Structure
- **config/**: Django project configuration and settings
  - `settings.py`: Main Django settings with django-environ integration
  - `urls.py`: Root URL configuration
  - `wsgi.py`/`asgi.py`: WSGI/ASGI application entry points

- **automation/**: Main Django app for network automation
  - Contains views, models, and URL routing for automation features
  - `views.py`: Currently contains healthcheck endpoint
  - `urls.py`: App-specific URL patterns

### Configuration Management
The project uses django-environ for environment-based configuration:
- `.env.example`: Template for environment variables
- `.env`: Local environment configuration (not in version control)
- Environment variables: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`

### Database
- Development: SQLite (`db.sqlite3`)
- Migrations located in `automation/migrations/`

### Network Automation Dependencies
Key packages for network automation:
- `netmiko==4.6.0`: Multi-vendor network device library
- `paramiko==4.0.0`: SSH client for Python
- `textfsm==2.1.0`: Template-based parsing
- `ntc_templates==8.1.0`: Network device command templates

## Health Check

The application includes a basic health check endpoint:
- **GET** `/health/` - Returns `{"status": "ok"}` for monitoring

## Development Notes

- The project follows standard Django project structure with a dedicated config package
- Virtual environment is located in `.venv/` directory
- SQLite database file (`db.sqlite3`) is in the project root
- The automation app is registered in Django settings but currently minimal

## Environment Variables

Required environment variables (see `.env.example`):
- `DJANGO_SECRET_KEY`: Django secret key for cryptographic signing
- `DJANGO_DEBUG`: Enable/disable debug mode (true/false)
- `DJANGO_ALLOWED_HOSTS`: Comma-separated list of allowed hosts