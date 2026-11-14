# Urban Nest

Urban Nest is a web application for finding and booking apartments. It provides authenticated apartment search, date-based availability, booking management, long-stay payment periods, and a Daraja M-Pesa Sandbox integration.

## Purpose

The project gives guests a single place to discover apartments, check date availability, book a stay, and track payment status. Apartment listings use server-side pagination so the API can serve larger inventories without returning every listing in one response.

## Main features

- Account registration and login with JWT access and refresh tokens.
- Apartment search by text and availability dates.
- Server-side page-number pagination (20 apartments per page).
- Individual apartment pages with descriptions, ratings, reviews, and date availability.
- Short stays and generated 30-day payment periods for long stays.
- Booking ownership and cancellation rules.
- Daraja STK Push and callback handling restricted to Sandbox.
- Dashboard announcements and payment due counts.

## Technologies

- Python 3.13, Django, Django REST Framework, Simple JWT.
- PostgreSQL with psycopg 3.
- React, React Router, Vite, Tailwind CSS.
- Safaricom Daraja Sandbox.

## Project structure

    plots/
      manage.py
      config/                  Django settings, URL routing, ASGI and WSGI
      plots/                   Django application and migrations
        api/                   API views, serializers and URL routes
        management/            Management commands
      bookit-ui/               React and Vite application
    docs/
      API.md                   API reference

## Requirements

- Python 3.13.
- PostgreSQL 14 or later, installed and running locally.
- Node.js and npm.
- Daraja Sandbox credentials only if exercising the payment integration.

## PostgreSQL setup

The backend reads configuration from plots/.env. Copy plots/.env.example to plots/.env and set a private database username and password. The SQLite database file is retained as an archive; it is not automatically imported into PostgreSQL.

Install PostgreSQL and start its service. Connect as a PostgreSQL administrator and create a database and a least-privilege application role. For example, in psql:

    CREATE DATABASE urban_nest;
    CREATE USER urban_nest_user WITH PASSWORD 'choose-a-private-password';
    GRANT ALL PRIVILEGES ON DATABASE urban_nest TO urban_nest_user;

Set DB_NAME, DB_USER, DB_PASSWORD, DB_HOST and DB_PORT in plots/.env to match the local database and role. Do not commit plots/.env.

## Backend setup

From the repository root, create and activate a virtual environment, then install dependencies:

    py -3.13 -m venv myenv
    .myenvScriptsActivate.ps1
    pip install -r plotsequirements.txt

On macOS or Linux, activate with source myenv/bin/activate.

Copy the example environment file and configure its values:

    Copy-Item plots.env.example plots.env

Set DJANGO_SECRET_KEY to a newly generated private key. Set DJANGO_DEBUG=true and DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 for local development. Configure the DB_* settings above. Daraja settings can remain blank until Sandbox is configured; MPESA_ENVIRONMENT must remain sandbox.

For a new PostgreSQL database, initialize the schema and create an administrator:

    Set-Location plots
    python manage.py check
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py runserver

Migration commands are shown for your local setup. No database migration or data transfer is performed by this project documentation.

## Frontend setup

In another terminal:

    Set-Location plotsookit-ui
    npm ci
    npm run dev

The Vite development server proxies API traffic to Django at http://127.0.0.1:8000.

## Tests and production build

Backend, from plots/ (test settings use an isolated in-memory SQLite database):

    python manage.py check
    python manage.py makemigrations --check --dry-run
    python manage.py test --settings=config.test_settings

Frontend, from plots/bookit-ui/:

    npm.cmd run lint
    npm.cmd run build

Payment tests should mock Safaricom requests. Never test by initiating a real payment.

## API documentation

See [docs/API.md](docs/API.md) for route methods, authentication, and request/response examples.

