# Urban Nest API

All endpoints are under `/api/`. Unless stated otherwise, they require an authenticated customer or manager. API authentication uses the existing JWT/token/session architecture.

## Customer

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/auth/register/` | Register a customer |
| POST | `/api/auth/login/` | Log in |
| GET | `/api/auth/me/` | Current account and role |
| GET | `/api/houses/` | Paginated active listings, optionally filtered by dates/search |
| GET | `/api/houses/{id}/` | Listing details, photos, reviews, and date availability |
| GET, POST | `/api/bookings/` | List own bookings or submit a booking request |
| GET | `/api/bookings/{id}/` | Retrieve an owned booking |
| POST | `/api/bookings/{id}/cancel/` | Cancel an owned pending or confirmed booking |
| GET | `/api/notifications/` | List own booking notifications and unread count |
| POST | `/api/notifications/{id}/read/` | Mark an owned notification read |
| GET | `/api/dashboard/` | Customer announcements and unread notification count |

Booking submissions require `house`, `check_in`, `check_out`, `contact_number`, and `guest_count`. `total_price`, `status`, and `created_at` are server controlled. New requests are always pending, and cost is calculated from the stored nightly price.

## Manager

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/manager/dashboard/` | Apartment, tenant, booking, and unread-request summaries |
| GET, POST | `/api/manager/apartments/` | List or create apartment listings |
| GET, PATCH, DELETE | `/api/manager/apartments/{id}/` | View, edit, or deactivate a listing |
| POST | `/api/manager/apartments/{id}/photos/` | Add a listing photo |
| PUT, DELETE | `/api/manager/apartments/{id}/photos/{photo_id}/` | Replace or remove a listing photo |
| GET | `/api/manager/bookings/` | List booking requests and reservations, with status/search filters |
| GET | `/api/manager/booking-requests/unread-count/` | Current manager's unread request count |
| GET | `/api/manager/bookings/{id}/` | View a request and mark it read |
| POST | `/api/manager/bookings/{id}/approve/` | Approve a pending request after rechecking availability |
| POST | `/api/manager/bookings/{id}/reject/` | Reject a pending request |
| GET, POST | `/api/manager/announcements/` | List or create announcements |
| GET | `/api/manager/tenants/` | List customers |
| GET, PATCH | `/api/manager/tenants/{id}/` | View or deactivate a customer account |
| GET, POST | `/api/manager/invitations/` | Manage manager invitations (main manager only) |
| GET | `/api/manager/managers/` | List managers (main manager only) |

Manager approval locks the apartment row and checks for overlapping confirmed bookings inside a transaction. A conflicting request remains pending. Pending, rejected, and cancelled requests do not reserve dates.

A Django superuser has manager access. Create the first local manager interactively with `python manage.py createsuperuser`; do not use a hardcoded password.

## Notifications and email

A booking submission creates a customer notification and unread manager request notifications. Approval or rejection creates a customer decision notification. Notification rows are unique per user, booking, and notification type. Email uses Django's configured backend; a delivery error does not undo a booking change.
