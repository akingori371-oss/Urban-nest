import os
import sys
import getpass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.conf import settings
from django.db import connections, transaction
from django.core.management.color import no_style
from plots.models import House, HousePhoto

HOUSE_IDS = [
    1, 2, 3, 4, 5,
    11, 12, 13, 14, 15,
    21, 22, 23, 24, 25,
    31, 32, 33, 34, 35,
    41, 42, 43, 44, 45,
]

HOST = "dpg-dbtb6ejm8hqs73adjs8g-a.oregon-postgres.render.com"

username = input("New Render database username: ").strip()
password = getpass.getpass("New Render database password: ")

if not username or not password:
    raise SystemExit("Missing credentials.")

db = settings.DATABASES["default"].copy()
db.update({
    "NAME": "urban_nest",
    "USER": username,
    "PASSWORD": password,
    "HOST": HOST,
    "PORT": "5432",
    "CONN_MAX_AGE": 0,
    "OPTIONS": {
        "sslmode": "require",
        "channel_binding": "disable",
    },
})

connections.databases["production"] = db

houses = list(House.objects.filter(id__in=HOUSE_IDS).order_by("id"))

photos = list(
    HousePhoto.objects.filter(house_id__in=HOUSE_IDS)
    .exclude(caption__icontains="temporary low-resolution placeholder")
    .order_by("id")
)

if len(houses) != 25 or len(photos) != 50:
    raise SystemExit("Source validation failed. Nothing was transferred.")

for house in houses:
    house_photos = [p for p in photos if p.house_id == house.id]
    if not house.is_active or house.approval_status != "approved":
        raise SystemExit(f"House {house.id} is not approved and active.")
    if len(house_photos) != 2:
        raise SystemExit(f"House {house.id} does not have exactly two photos.")
    if house.owner_id is not None or house.reviewed_by_id is not None:
        raise SystemExit(f"House {house.id} has a user relationship. Transfer stopped.")

production = connections["production"]

try:
    production.ensure_connection()

    existing_houses = set(
        House.objects.using("production")
        .filter(id__in=HOUSE_IDS)
        .values_list("id", flat=True)
    )

    photo_ids = [p.id for p in photos]
    existing_photos = set(
        HousePhoto.objects.using("production")
        .filter(id__in=photo_ids)
        .values_list("id", flat=True)
    )

    if existing_houses or existing_photos:
        raise SystemExit(
            f"Safety stop. Conflicting house IDs: {existing_houses}; "
            f"conflicting photo IDs: {existing_photos}. Nothing imported."
        )

    print("\nSource verified: 25 apartments, 50 photos.")
    print("Production connection verified.")
    print("No conflicting IDs found.")

    confirmation = input(
        "\nType IMPORT URBAN NEST to transfer these records to production: "
    )

    if confirmation != "IMPORT URBAN NEST":
        raise SystemExit("Cancelled. No production records were changed.")

    with transaction.atomic(using="production"):
        house_copies = [
            House(
                id=h.id,
                name=h.name,
                county=h.county,
                location=h.location,
                property_type=h.property_type,
                description=h.description,
                bedrooms=h.bedrooms,
                price_per_night=h.price_per_night,
                amenities=h.amenities,
                is_active=h.is_active,
                owner_id=None,
                approval_status=h.approval_status,
                reviewed_by_id=None,
                reviewed_at=h.reviewed_at,
                created_at=h.created_at,
                updated_at=h.updated_at,
            )
            for h in houses
        ]

        House.objects.using("production").bulk_create(house_copies)

        photo_copies = [
            HousePhoto(
                id=p.id,
                house_id=p.house_id,
                image=p.image.name,
                caption=p.caption,
                created_at=p.created_at,
            )
            for p in photos
        ]

        HousePhoto.objects.using("production").bulk_create(photo_copies)

        # Restore original timestamps after bulk insertion.
        for h in houses:
            House.objects.using("production").filter(id=h.id).update(
                created_at=h.created_at,
                updated_at=h.updated_at,
            )

        for p in photos:
            HousePhoto.objects.using("production").filter(id=p.id).update(
                created_at=p.created_at,
            )

        # Reset PostgreSQL ID sequences after preserving the original IDs.
        with production.cursor() as cursor:
            for sql in production.ops.sequence_reset_sql(
                no_style(), [House, HousePhoto]
            ):
                cursor.execute(sql)

        imported_houses = House.objects.using("production").filter(
            id__in=HOUSE_IDS
        ).count()

        imported_photos = HousePhoto.objects.using("production").filter(
            id__in=photo_ids
        ).count()

        if imported_houses != 25 or imported_photos != 50:
            raise RuntimeError(
                f"Verification failed: {imported_houses} houses, "
                f"{imported_photos} photos."
            )

    print("\nSUCCESS! TRANSFER COMPLETED.")
    print("Apartments imported:", imported_houses)
    print("Genuine photos imported:", imported_photos)
    print("Original IDs and Cloudinary image paths preserved.")

finally:
    production.close()
PYcat > transfer_demo_houses.py <<'PY'
import os
import sys
import getpass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.conf import settings
from django.db import connections, transaction
from django.core.management.color import no_style
from plots.models import House, HousePhoto

HOUSE_IDS = [
    1, 2, 3, 4, 5,
    11, 12, 13, 14, 15,
    21, 22, 23, 24, 25,
    31, 32, 33, 34, 35,
    41, 42, 43, 44, 45,
]

HOST = "dpg-dbtb6ejm8hqs73adjs8g-a.oregon-postgres.render.com"

username = input("New Render database username: ").strip()
password = getpass.getpass("New Render database password: ")

if not username or not password:
    raise SystemExit("Missing credentials.")

db = settings.DATABASES["default"].copy()
db.update({
    "NAME": "urban_nest",
    "USER": username,
    "PASSWORD": password,
    "HOST": HOST,
    "PORT": "5432",
    "CONN_MAX_AGE": 0,
    "OPTIONS": {
        "sslmode": "require",
        "channel_binding": "disable",
    },
})

connections.databases["production"] = db

houses = list(House.objects.filter(id__in=HOUSE_IDS).order_by("id"))

photos = list(
    HousePhoto.objects.filter(house_id__in=HOUSE_IDS)
    .exclude(caption__icontains="temporary low-resolution placeholder")
    .order_by("id")
)

if len(houses) != 25 or len(photos) != 50:
    raise SystemExit("Source validation failed. Nothing was transferred.")

for house in houses:
    house_photos = [p for p in photos if p.house_id == house.id]
    if not house.is_active or house.approval_status != "approved":
        raise SystemExit(f"House {house.id} is not approved and active.")
    if len(house_photos) != 2:
        raise SystemExit(f"House {house.id} does not have exactly two photos.")
    if house.owner_id is not None or house.reviewed_by_id is not None:
        raise SystemExit(f"House {house.id} has a user relationship. Transfer stopped.")

production = connections["production"]

try:
    production.ensure_connection()

    existing_houses = set(
        House.objects.using("production")
        .filter(id__in=HOUSE_IDS)
        .values_list("id", flat=True)
    )

    photo_ids = [p.id for p in photos]
    existing_photos = set(
        HousePhoto.objects.using("production")
        .filter(id__in=photo_ids)
        .values_list("id", flat=True)
    )

    if existing_houses or existing_photos:
        raise SystemExit(
            f"Safety stop. Conflicting house IDs: {existing_houses}; "
            f"conflicting photo IDs: {existing_photos}. Nothing imported."
        )

    print("\nSource verified: 25 apartments, 50 photos.")
    print("Production connection verified.")
    print("No conflicting IDs found.")

    confirmation = input(
        "\nType IMPORT URBAN NEST to transfer these records to production: "
    )

    if confirmation != "IMPORT URBAN NEST":
        raise SystemExit("Cancelled. No production records were changed.")

    with transaction.atomic(using="production"):
        house_copies = [
            House(
                id=h.id,
                name=h.name,
                county=h.county,
                location=h.location,
                property_type=h.property_type,
                description=h.description,
                bedrooms=h.bedrooms,
                price_per_night=h.price_per_night,
                amenities=h.amenities,
                is_active=h.is_active,
                owner_id=None,
                approval_status=h.approval_status,
                reviewed_by_id=None,
                reviewed_at=h.reviewed_at,
                created_at=h.created_at,
                updated_at=h.updated_at,
            )
            for h in houses
        ]

        House.objects.using("production").bulk_create(house_copies)

        photo_copies = [
            HousePhoto(
                id=p.id,
                house_id=p.house_id,
                image=p.image.name,
                caption=p.caption,
                created_at=p.created_at,
            )
            for p in photos
        ]

        HousePhoto.objects.using("production").bulk_create(photo_copies)

        # Restore original timestamps after bulk insertion.
        for h in houses:
            House.objects.using("production").filter(id=h.id).update(
                created_at=h.created_at,
                updated_at=h.updated_at,
            )

        for p in photos:
            HousePhoto.objects.using("production").filter(id=p.id).update(
                created_at=p.created_at,
            )

        # Reset PostgreSQL ID sequences after preserving the original IDs.
        with production.cursor() as cursor:
            for sql in production.ops.sequence_reset_sql(
                no_style(), [House, HousePhoto]
            ):
                cursor.execute(sql)

        imported_houses = House.objects.using("production").filter(
            id__in=HOUSE_IDS
        ).count()

        imported_photos = HousePhoto.objects.using("production").filter(
            id__in=photo_ids
        ).count()

        if imported_houses != 25 or imported_photos != 50:
            raise RuntimeError(
                f"Verification failed: {imported_houses} houses, "
                f"{imported_photos} photos."
            )

    print("\nSUCCESS! TRANSFER COMPLETED.")
    print("Apartments imported:", imported_houses)
    print("Genuine photos imported:", imported_photos)
    print("Original IDs and Cloudinary image paths preserved.")

finally:
    production.close()
