# NetAuto Platform (Django + Netmiko)

A network automation platform for Huawei and Cisco switches/routers using Python Netmiko for device automation and Django for a web GUI.

- Backend: Django
- Network: Netmiko (Cisco, Huawei)
- Config: django-environ (.env)

Quickstart (after installing Python 3.12+ and Git):
1. python -m venv .venv
2. .\.venv\Scripts\Activate.ps1  # PowerShell
3. pip install -r requirements.txt
4. python manage.py migrate
5. python manage.py runserver

Healthcheck: GET /health/
"# netauto-platform" 
