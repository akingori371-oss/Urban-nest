from django.shortcuts import render , redirect
from django.contrib.auth.forms import UserCreationForm

DUMMY_HOUSES = [
    {"id": 1, "name": "Sunset Villa", "location": "Nairobi", "bedrooms": 4,
     "price_per_night": 120, "description": "Spacious and bright.", "avg_rating": 4.5, "review_count": 8},
    {"id": 2, "name": "City Loft", "location": "Nairobi", "bedrooms": 1,
     "price_per_night": 50, "description": "Close to everything.", "avg_rating": None, "review_count": 0},
    {"id": 3, "name": "Garden House", "location": "Karuri", "bedrooms": 3,
     "price_per_night": 90, "description": "Quiet with a garden.", "avg_rating": 4.0, "review_count": 3},
]

def landing(request):
    return render(request , "landing.html")

def signup(request):
    form = UserCreationForm()
    return render(request , "accounts/signup.html" , {"form" : form})
def dashboard(request):
    context = {    "due_count": 2,
        "announcements": [
            {"title": "Water maintenance", "message": "Water will be off Friday 9am to 12pm.", "created_at": None},
            {"title": "New listing", "message": "Hilltop Retreat is now available.", "created_at": None},
        ],
    }
    return render(request , "dashboard.html" , context)
def house_list(request):
    return render(request , "bookings/houses.html" , {
        "houses":DUMMY_HOUSES,"favs":{1},"searched":False,
        "check_in":"","check_out":"",
    })