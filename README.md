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
- A role-protected manager workspace for apartment, booking, payment, announcement, tenant, and invitation management.

## Technologies

- Python 3.13, Django, Django REST Framework, Simple JWT.
- PostgreSQL with psycopg 3.
- React, React Router, Vite, Tailwind CSS.
- Safaricom Daraja Sandbox.

## Project structure

    plots/
      config/                  Django settings, URL routing, ASGI and WSGI
      plots/                   Django application, management command and migrations
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

The backend reads configuration from `plots/.env`; keep database credentials private and do not commit this file. The SQLite database file is retained as an archive; it is not imported into PostgreSQL.

Install PostgreSQL and start its service. Connect as a PostgreSQL administrator and create a database and a least-privilege application role. For example, in psql:

    CREATE DATABASE urban_nest;
    CREATE USER urban_nest_user WITH PASSWORD 'choose-a-private-password';
    GRANT ALL PRIVILEGES ON DATABASE urban_nest TO urban_nest_user;

Set DB_NAME, DB_USER, DB_PASSWORD, DB_HOST and DB_PORT in plots/.env to match the local database and role. Do not commit plots/.env.

## Backend setup

From the repository root, create and activate a virtual environment, then install dependencies:

    py -3.13 -m venv myenv
    .\myenv\Scripts\Activate.ps1
    pip install -r plots/requirements.txt

On macOS or Linux, activate with `source myenv/bin/activate`.

Configure `plots/.env` with `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=true`, `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`, and the PostgreSQL `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` and `DB_PORT` values. Keep the file private. `DB_NAME` should be `urban_nest` for the local application database.

For a new PostgreSQL database, initialize the schema and create an administrator from the repository root:

    python plots/plots/manage.py check
    python plots/plots/manage.py migrate
    python plots/plots/manage.py createsuperuser
    python plots/plots/manage.py runserver

## Frontend setup

In another terminal, from the repository root:

    Set-Location plots/bookit-ui
    npm ci
    npm run dev

The Vite development server proxies API traffic to Django at http://127.0.0.1:8000.

## Tests, migrations and production build

Run the backend verification commands from the repository root. The test settings use an isolated in-memory SQLite database; normal application settings continue to use PostgreSQL.

    python plots/plots/manage.py check
    python plots/plots/manage.py makemigrations --check --dry-run
    python plots/plots/manage.py showmigrations plots
    python plots/plots/manage.py migrate --plan
    python plots/plots/manage.py test plots --settings=config.test_settings

Before testing or merging backend changes, confirm `makemigrations --check --dry-run` reports no model changes without migration files, inspect `showmigrations` and `migrate --plan` for pending schema work, and include migration files in version control (`git status --short`). Generate schema changes with `python plots/plots/manage.py makemigrations plots`, review the operations and dependencies, and commit the migration file with its model change. Apply reviewed migrations to the intended PostgreSQL database with `python plots/plots/manage.py migrate` only after checking `DB_NAME` and the planned operations. Do not use `--fake` to work around a schema mismatch.

## Fictional demo apartments

The 50-listing demonstration seed is repeatable, creates only listings with missing stable demo identifiers, and never creates users, bookings, payments, reviews, or photos. Preview it first, then run it only after the required House schema migration is applied:

    python plots/plots/manage.py seed_demo_apartments --dry-run
    python plots/plots/manage.py seed_demo_apartments

Demo monthly rent is stored as a nightly equivalent (`monthly rent / 30`) for existing booking calculations; the listing UI labels the provided source amount as monthly. Sample ratings are explicitly labeled fictional and kept separate from genuine review averages. No apartment image assets were supplied, so the existing image behavior is unchanged.

Frontend, from plots/bookit-ui/:

    npm.cmd test
    npm.cmd run lint
    npm.cmd run build

Payment tests should mock Safaricom requests. Never test by initiating a real payment.

## API documentation

See [docs/API.md](docs/API.md) for route methods, authentication, and request/response examples.

Manager setup, roles, invitation workflow, and media storage are documented in the [manager API section](docs/API.md#manager-api).

