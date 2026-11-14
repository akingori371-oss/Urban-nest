# Urban Nest

Urban Nest is a Django REST Framework booking API with a React/Vite client. Stays longer than 30 nights have 30-day payment periods. M-Pesa uses Safaricom Daraja STK Push and is restricted to Sandbox.

## Requirements

- Python 3.13
- Node.js and npm
- Daraja Sandbox app and a publicly reachable HTTPS callback URL for end-to-end payment testing

## Backend setup (PowerShell)

From the repository root:

    py -3.13 -m venv myenv
    .myenvScriptsActivate.ps1
    pip install -r plotsequirements.txt
    $env:DJANGO_SECRET_KEY = (py -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
    $env:DJANGO_DEBUG = "true"
    $env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1"
    $env:MPESA_ENVIRONMENT = "sandbox"
    $env:MPESA_CONSUMER_KEY = "<Sandbox consumer key>"
    $env:MPESA_CONSUMER_SECRET = "<Sandbox consumer secret>"
    $env:MPESA_PASSKEY = "<Sandbox passkey>"
    $env:MPESA_SHORTCODE = "174379"
    $env:MPESA_CALLBACK_URL = "<public HTTPS callback URL>/api/mpesa/callback/"
    Set-Location plots
    python manage.py check
    python manage.py runserver

Keep local credentials in an ignored .env file if preferred; never commit it. DJANGO_SECRET_KEY is required. DEBUG defaults to false and ALLOWED_HOSTS defaults to loopback hosts. Production Daraja is rejected.

## Frontend setup

In another terminal:

    Set-Location plotsookit-ui
    npm ci
    npm run dev

Vite proxies /api requests to Django at http://127.0.0.1:8000.

## API overview

All routes are mounted under /api/. Authentication uses Simple JWT bearer access tokens.

- POST /auth/register/, POST /auth/login/, POST /auth/token/refresh/
- GET /auth/me/, GET /houses/
- GET and POST /bookings/, POST /bookings/<id>/cancel/
- GET /bookings/<id>/periods/
- POST /pay/booking/<id>/, POST /pay/period/<id>/
- GET /payments/<id>/ (owner-only status and receipt)
- POST /mpesa/callback/ (Daraja callback)
- GET /dashboard/

The frontend uses Authorization: Bearer <access token>. Successful callbacks update the booking or period; payment status includes the receipt for its owner.

## Database and migrations

SQLite is used for local development. On a new local database, run python manage.py migrate. Migration 0005 is included but was not applied to the existing database in this workspace. Back up local data before applying migrations yourself.

## Verification

From plots/ run python manage.py check, python manage.py makemigrations --check --dry-run, and python manage.py test. From plots/bookit-ui/ run npm.cmd run lint and npm.cmd run build. Automated payment tests mock Daraja initiation and do not make real requests.
