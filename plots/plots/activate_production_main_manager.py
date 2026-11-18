import os
import sys
import getpass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connections, transaction
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

    print("\nThis will make your existing account the Main Manager.")
    print("No new account or password changes will be made.")

    confirmation = input(
        '\nType "MAKE MY ACCOUNT MAIN MANAGER" to continue: '
    )

    if confirmation != "MAKE MY ACCOUNT MAIN MANAGER":
        print("Cancelled. No changes were made.")
        sys.exit(0)

    User = get_user_model()

    with transaction.atomic(using="production"):
        users = list(
            User.objects.using("production")
            .select_for_update()
            .filter(email__iexact="akingori371@gmail.com")
        )

        if len(users) != 1:
            raise RuntimeError(
                f"Expected exactly one account, found {len(users)}."
            )

        user = users[0]

        if not user.is_active:
            raise RuntimeError("The account is inactive. No changes made.")

        existing_main = (
            ManagerProfile.objects.using("production")
            .select_for_update()
            .filter(is_main=True)
            .first()
        )

        if existing_main and existing_main.user_id != user.pk:
            raise RuntimeError(
                "Another account is already Main Manager. No changes made."
            )

        profile, created = (
            ManagerProfile.objects.using("production").update_or_create(
                user_id=user.pk,
                defaults={"is_main": True},
            )
        )

    verified = ManagerProfile.objects.using("production").get(
        user_id=user.pk
    )

    if not verified.is_main:
        raise RuntimeError("Verification failed.")

    print("\nSUCCESS: Your existing account is now the Main Manager.")
    print("User ID:", user.pk)
    print("Username:", user.username)
    print("Profile created:", created)
    print("Main Manager:", verified.is_main)

finally:
    connections["production"].close()
