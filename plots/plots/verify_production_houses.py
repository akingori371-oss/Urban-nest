import os
import sys
import getpass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.conf import settings
from django.db import connections
from django.db.models import Count
from plots.models import House, HousePhoto

HOUSE_IDS = [
    1, 2, 3, 4, 5,
    11, 12, 13, 14, 15,
    21, 22, 23, 24, 25,
    31, 32, 33, 34, 35,
    41, 42, 43, 44, 45,
]

username = input("Render database username: ").strip()
password = getpass.getpass("Render database password: ")

db = settings.DATABASES["default"].copy()
db.update({
    "NAME": "urban_nest",
    "USER": username,
    "PASSWORD": password,
    "HOST": "dpg-dbtb6ejm8hqs73adjs8g-a.oregon-postgres.render.com",
    "PORT": "5432",
    "CONN_MAX_AGE": 0,
    "OPTIONS": {
        "sslmode": "require",
        "channel_binding": "disable",
    },
})

connections.databases["production"] = db

try:
    connections["production"].ensure_connection()

    houses = list(
        House.objects.using("production")
        .filter(id__in=HOUSE_IDS)
        .annotate(photo_count=Count("photos"))
        .order_by("id")
    )

    photo_count = HousePhoto.objects.using("production").filter(
        house_id__in=HOUSE_IDS
    ).count()

    print("\nPRODUCTION DATABASE VERIFICATION")
    print("--------------------------------")
    print("Total apartments in production:", House.objects.using("production").count())
    print("Total photos in production:", HousePhoto.objects.using("production").count())
    print("Selected apartments found:", len(houses))
    print("Photos attached to selected apartments:", photo_count)

    print("\nAPARTMENT DETAILS")
    for house in houses:
        print(
            f"{house.id}: {house.name} | "
            f"Active: {house.is_active} | "
            f"Approval: {house.approval_status} | "
            f"Photos: {house.photo_count}"
        )

    valid = (
        len(houses) == 25
        and photo_count == 50
        and all(
            house.is_active
            and house.approval_status == "approved"
            and house.photo_count == 2
            for house in houses
        )
    )

    print("\nRESULT:", "VERIFICATION PASSED" if valid else "VERIFICATION FAILED")

finally:
    connections["production"].close()
