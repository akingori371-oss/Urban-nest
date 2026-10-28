BookIt API

A house booking REST API built with Django and Django REST Framework. Users register, log in with a token, search for houses that are free on their dates, book, and pay. Stays longer than 30 nights are split into 30-day payment periods.

The project also includes a server-rendered website (login, booking pages, owner dashboard), but this README focuses on the API.

Features
Token authentication: register, login, current user
Search houses and filter by check-in and check-out dates
Create and cancel bookings with server-side validation (no past dates, no double-booking)
Automatic total price (nights x price per night)
Payment periods for stays over 30 nights
Mock M-Pesa payment that returns a receipt
Per-user data access: users only see their own bookings
Superuser-only endpoints, plus Django admin for managing houses and announcements
Tech stack
Python 3.13
Django
Django REST Framework (with rest_framework.authtoken)
SQLite
Project structure
Urban-nest/
├── manage.py
└── plots/                  # project and app in one
    ├── settings.py
    ├── urls.py
    ├── models.py           # House, Booking, PaymentPeriod, Review, Announcement, Favorite, LoginEvent
    ├── views.py            # website views
    ├── forms.py
    ├── api/
    │   ├── urls.py
    │   ├── views.py        # API views
    │   └── serializers.py
    ├── management/
    │   └── commands/
    │       └── seed.py     # demo data
    └── templates/
Setup
bash
git clone <your-repo-url>
cd Urban-nest

python -m venv myenv
myenv\Scripts\activate          # Windows
# source myenv/bin/activate     # macOS / Linux

pip install django djangorestframework requests

python manage.py makemigrations plots
python manage.py migrate
python manage.py createsuperuser
python manage.py seed           # optional demo data
python manage.py runserver

The API is then available at http://127.0.0.1:8000/api/.

Required settings
python
INSTALLED_APPS = [
    # ...
    "rest_framework",
    "rest_framework.authtoken",
    "plots",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}
Demo data

python manage.py seed creates 6 houses, guests guest1 to guest10 (password pass12345), bookings, payment periods, reviews and login events. Re-running it rebuilds the guest accounts. Delete or change these accounts before deploying anywhere public.

Authentication

Register or log in to get a token, then send it in the Authorization header on every other request:

Authorization: Token <your token>

The word Token and the space after it are required.

Endpoints
Method	Endpoint	Access	Description
POST	/api/auth/register/	Anyone	Create an account, returns a token
POST	/api/auth/login/	Anyone	Log in, returns a token
GET	/api/auth/me/	User	Current user
GET	/api/houses/	User	List houses. Add ?check_in=YYYY-MM-DD&check_out=YYYY-MM-DD to see only free ones
GET	/api/bookings/	User	Your bookings
POST	/api/bookings/	User	Create a booking
POST	/api/bookings/<id>/cancel/	Owner	Cancel a booking
GET	/api/bookings/<id>/periods/	Owner	Payment periods of a long stay
POST	/api/pay/booking/<id>/	Owner	Pay a short stay (mock M-Pesa)
POST	/api/pay/period/<id>/	Owner	Pay one period of a long stay (mock M-Pesa)
GET	/api/dashboard/	User	Payments due and announcements
GET	/api/users/	Superuser	List all users
GET	/api/users/<id>/	Superuser	One user with their bookings
Example requests

Register

POST /api/auth/register/
{"username": "demo1", "email": "demo1@example.com", "password": "Pass12345!"}

Response: 201 with {"token": "...", "username": "demo1"}

Find free houses

GET /api/houses/?check_in=2026-12-01&check_out=2026-12-05

Create a booking

POST /api/bookings/
{"house": 1, "check_in": "2026-12-01", "check_out": "2026-12-05"}

house is the house id. The server sets the user from the token and calculates the total price.

Pay a short stay

POST /api/pay/booking/<booking id>/
{"phone": "0712345678"}

Response: {"status": "success", "receipt": "MOCK...", "amount": "175.00", ...}

Use the booking id (from the booking response), not the house id.

Business rules
Check-in cannot be in the past.
Check-out must be after check-in.
A house cannot be booked if a confirmed booking overlaps the dates. Cancelled bookings free the house.
A stay of 30 nights or less is paid once. A longer stay gets one payment period per 30 days (the last may be shorter).
Users can only view, cancel and pay their own bookings.
Status codes
Code	Meaning
200 / 201	Success / created
400	Validation failed (past date, already booked, already paid)
401	Missing or invalid token
403	Logged in but not allowed (for example a guest on a superuser endpoint)
404	Not found, or not yours
Testing with Postman
POST /api/auth/login/ with raw JSON and copy the token.
Add the header Authorization: Token <token> to later requests.
For POST requests, set Body to raw and the type to JSON.
Limitations
Payments are simulated and not connected to the real M-Pesa.
Tokens do not expire.
SQLite is used for development only.
Booking overlap is checked in the application, not by a database constraint.
Next steps
Real M-Pesa STK Push integration
Review and favorite endpoints
Superuser analytics endpoints
Expiring tokens or JWT