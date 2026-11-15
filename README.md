# Urban Nest

Urban Nest is an apartment reservation app. Customers browse listings, view nightly prices, and submit booking requests. A manager reviews every request before it becomes a confirmed reservation.

## Features

- Authenticated apartment browsing, listing photos, reviews, favorites, and announcements.
- Date-based booking requests with server-calculated estimated costs.
- Pending, confirmed, rejected, and cancelled booking states.
- Manager approval checks availability again while holding a database row lock.
- Persistent customer and manager notifications with unread request counts.
- Email notifications for submission and manager decisions.
- Manager tools for apartment listings, booking requests, announcements, tenants, and manager invitations.

Pending requests do not reserve dates. Only confirmed bookings prevent overlapping reservations.

## Local setup

From `plots/`:

```powershell
..\myenv\Scripts\python.exe plots\manage.py migrate
..\myenv\Scripts\python.exe plots\manage.py createsuperuser
..\myenv\Scripts\python.exe plots\manage.py runserver
```

The superuser created by `createsuperuser` has manager access. Choose its password interactively; the project does not provide a default account or password.

The React application is in `plots/bookit-ui`:

```powershell
npm install
npm run dev
```

## Environment configuration

Django reads `plots/.env`. Required values include `DJANGO_SECRET_KEY` and the local PostgreSQL connection settings (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`). Keep secrets out of source control and logs.

For local development, email defaults to Django's console backend. The console backend writes messages to the Django terminal; it does not deliver email externally. To deliver email, configure `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and the appropriate `EMAIL_USE_TLS` or `EMAIL_USE_SSL` values. Email failures do not undo bookings or manager decisions, and API responses do not claim delivery.

## Booking API

A customer submits a request with `house`, `check_in`, `check_out`, `contact_number`, and `guest_count` at `POST /api/bookings/`. The server calculates `total_price` from the listing's nightly price and creates the request as pending. A customer cannot set the status through the API.

Managers use `GET /api/manager/bookings/` and the Booking Requests dashboard. Request details are available at `GET /api/manager/bookings/{id}/`; approvals and rejections use `POST /api/manager/bookings/{id}/approve/` and `/reject/`. A request is marked read when its manager detail is opened. The unread count is returned by `GET /api/manager/booking-requests/unread-count/`.

Customers can view their bookings at `GET /api/bookings/`, view one at `GET /api/bookings/{id}/`, and view or mark their notifications through `/api/notifications/` and `/api/notifications/{id}/read/`.

## Development checks

From the project root:

```powershell
.\myenv\Scripts\python.exe -B plots\plots\manage.py test plots --settings=config.test_settings
cd plots/bookit-ui
npm.cmd test
npm.cmd run build
npm.cmd run lint
```

The backend test settings use an in-memory SQLite database. Tests use Django's mock email backend.
