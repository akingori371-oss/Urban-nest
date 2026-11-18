import os
import sys
import getpass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connections
from plots.models import ManagerProfile

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
    "OPTIONS": {"sslmode": "require", "channel_binding": "disable"},
})
connections.databases["production"] = db

try:
    connections["production"].ensure_connection()

    User = get_user_model()
    target = User.objects.using("production").filter(
        email__iexact="akingori371@gmail.com"
    )

    print("\nEXISTING ACCOUNT")
    print("Matching accounts:", target.count())

    for user in target:
        print("User ID:", user.pk)
        print("Username:", user.username)
        print("Active:", user.is_active)
        print("Superuser:", user.is_superuser)
        print("Has manager profile:", ManagerProfile.objects.using("production").filter(user_id=user.pk).exists())

    print("\nCURRENT MANAGERS")
    profiles = ManagerProfile.objects.using("production").select_related("user")
    print("Manager profiles:", profiles.count())
    print("Main managers:", profiles.filter(is_main=True).count())

    for profile in profiles:
        print(
            f"User ID: {profile.user_id} | "
            f"Email: {profile.user.email} | "
            f"Main: {profile.is_main}"
        )

finally:
    connections["production"].close()
