# Urban Nest API

All routes use the /api/ prefix. Protected routes require an access token:

    Authorization: Bearer <access-token>

Registration and login return JWT access and refresh tokens. Use the refresh endpoint to obtain a new access token. API errors generally return a detail field.

## Authentication

| Method | Route | Auth | Purpose |
|---|---|---|---|
| POST | /api/auth/register/ | No | Create an account |
| POST | /api/auth/login/ | No | Log in using email and password |
| POST | /api/auth/token/refresh/ | No | Refresh an access token |
| GET | /api/auth/me/ | Yes | Get the authenticated user |

Registration request:

    {"username":"amina","email":"amina@example.com","password":"a-strong-password"}

Registration and login return access, refresh, and username fields.

## Apartments

| Method | Route | Auth | Purpose |
|---|---|---|---|
| GET | /api/houses/ | Yes | Search and paginate apartments |
| GET | /api/houses/{id}/ | Yes | Retrieve one apartment |

Listings use page-number pagination with 20 results per page. The response contains count, next, previous, and results.

Example:

    GET /api/houses/?page=1&search=nairobi&check_in=2026-12-01&check_out=2026-12-05

The detail route accepts check_in and check_out query parameters to include a date-specific availability boolean. Without both dates, availability is null. The detail payload also includes description, bedroom count, nightly price, average rating, review count, and review summaries.

## Bookings

| Method | Route | Auth | Purpose |
|---|---|---|---|
| GET | /api/bookings/ | Yes | List the caller's bookings |
| POST | /api/bookings/ | Yes | Create a booking |
| POST | /api/bookings/{id}/cancel/ | Yes | Cancel an unpaid booking |
| GET | /api/bookings/{id}/periods/ | Yes | List long-stay payment periods |

Create request:

    {"house":15,"check_in":"2026-12-01","check_out":"2026-12-05"}

Dates use YYYY-MM-DD. Check-in must not be in the past, check-out must be later than check-in, and confirmed bookings may not overlap. Adjacent stays are allowed. Users can access only their own bookings.

## Payments

| Method | Route | Auth | Purpose |
|---|---|---|---|
| POST | /api/pay/booking/{id}/ | Yes | Start payment for a short stay |
| POST | /api/pay/period/{id}/ | Yes | Start payment for a long-stay period |
| GET | /api/payments/{id}/ | Yes | Retrieve owner-only payment status and receipt |
| POST | /api/mpesa/callback/ | Daraja callback | Receive an STK Push callback |

Payment initiation request:

    {"phone":"0712345678"}

Payment status returns id, status, booking or period target, amount, receipt, result_code, and result_description. Status values include pending, success, failed, and review. A receipt is present after a validated successful callback.

The callback route is called by Daraja and does not use guest JWT authentication. The backend checks the checkout ID, merchant request ID when recorded, and transaction details before applying a successful payment. Only Sandbox is configured.

## Dashboard

| Method | Route | Auth | Purpose |
|---|---|---|---|
| GET | /api/dashboard/ | Yes | Return due, overdue and future payment counts and recent announcements |

The response includes payments_due, payments_overdue, payments_due_now, payments_future, and announcements.
