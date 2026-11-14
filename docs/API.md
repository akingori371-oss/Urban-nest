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

## Manager API

All manager routes use the existing JWT `Authorization: Bearer <access-token>` header. Operational routes accept main and invited managers; manager invitation, manager listing, and manager removal routes accept only the main manager. Django superusers also retain root manager access. These permissions are enforced by the backend.

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/manager/dashboard/` | Actual apartment, tenant, booking, payment, balance, and recent activity summaries |
| GET, POST | `/api/manager/apartments/` | Search/paginate apartments; create apartment |
| GET, PATCH, DELETE | `/api/manager/apartments/{id}/` | Read/update apartment; DELETE safely deactivates it |
| POST | `/api/manager/apartments/{id}/photos/` | Upload JPEG, PNG, or WebP up to 8 MB |
| PUT, DELETE | `/api/manager/apartments/{id}/photos/{photo_id}/` | Replace or remove an apartment photograph |
| GET | `/api/manager/bookings/` | Paginated all-tenant bookings; supports `search`, `status`, `apartment`, `tenant`, `check_in_from`, and `check_in_to` |
| GET, POST | `/api/manager/bookings/{id}/` | View details and payment periods; POST with `{"status":"cancelled"}` cancels a confirmed booking |
| GET | `/api/manager/payments/` | Paginated platform M-Pesa records; supports `search`, `status`, `tenant`, `apartment`, `date_from`, and `date_to`; read-only |
| GET, POST | `/api/manager/announcements/` | List and create announcements |
| PATCH, DELETE | `/api/manager/announcements/{id}/` | Edit/publish/unpublish or delete an announcement |
| GET | `/api/manager/tenants/` | Search/paginate tenants; supports `search` and `active` |
| GET, PATCH | `/api/manager/tenants/{id}/` | View history; PATCH `{"is_active":false}` deactivates or reactivates a tenant |
| GET, POST | `/api/manager/invitations/` | Main-manager pending/accepted invitation list and invitation creation |
| DELETE | `/api/manager/invitations/{id}/` | Main-manager cancellation of a pending invitation |
| GET | `/api/manager/managers/` | Main-manager list of managers |
| DELETE | `/api/manager/managers/{id}/` | Main-manager removal of an invited manager's manager role |
| POST | `/api/manager/invitations/accept/{token}/` | Authenticated invitee accepts the single-use emailed token using the invited account email |

Apartment deletion preserves booking/payment history by setting `is_active=false`. Manager payment APIs are read-only; there is no endpoint that can manually mark a payment successful. The existing Daraja callback remains responsible for verified payment success. Dashboard occupancy counts confirmed bookings covering the current date. Outstanding balances include unpaid confirmed short bookings and long-stay periods.

### Manager account setup

The initial account must first be created through normal registration using `akingori371@gmail.com`. The controlled command `python manage.py provision_main_manager` sends an expiring verification link to that address; it does not grant privileges until the account is authenticated and the single-use link is accepted. Invited managers are granted an application role only after accepting their own email invitation. Neither manager role sets Django `is_staff` or `is_superuser`.

The current project email configuration uses Django's console mail backend. Manager invitation creation and initial provisioning deliberately fail closed while that backend is active. A secure delivery backend must be configured before those workflows can be used; no SMTP credentials or outbound email backend were added in this change. Use Django `MAILERS` configuration and private deployment settings for mail host, port, username, password, TLS, and sender address. Set `URBAN_NEST_FRONTEND_URL` to the deployed React origin so email links return to the app.

Uploaded photographs use Django's configured `MEDIA_ROOT` storage under `houses/YYYY/MM/`. In development, media URLs are served only when `DEBUG` is enabled. Production must serve the configured media storage through the deployment's static/media server or object storage.

The React manager area starts at `/manager`. The frontend provides dashboard, apartment, booking, payment, announcement, tenant, manager, and invitation screens. Only main managers see manager/invitation controls. The invitee opens `/manager/invitations/accept/{token}`, logs in or registers with the invited email, then accepts the link.
