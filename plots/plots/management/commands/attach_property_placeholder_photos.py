from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import transaction

from plots.models import House, HousePhoto
from plots.management.commands.seed_demo_apartments import DEMO_APARTMENTS, marker_for


PLACEHOLDER_DIR = Path("property_placeholders")


class Command(BaseCommand):
    help = "Attach the supplied temporary interior and exterior photos to the 50 demo properties."

    def handle(self, *args, **options):
        created = 0
        skipped = 0

        with transaction.atomic():
            for number, apartment in enumerate(DEMO_APARTMENTS, start=1):
                marker = marker_for(apartment)
                house = House.objects.filter(description__startswith=marker).first()
                if house is None:
                    raise CommandError(f"No property record found for property-{number:02d} ({apartment[0]}).")

                for view in ("interior", "exterior"):
                    filename = f"property-{number:02d}-{view}.jpg"
                    relative_path = PLACEHOLDER_DIR / filename
                    image_name = relative_path.as_posix()
                    if not (settings.MEDIA_ROOT / relative_path).is_file():
                        raise CommandError(f"Missing image file: {settings.MEDIA_ROOT / relative_path}")

                    matching_photos = HousePhoto.objects.filter(house=house, image=image_name).order_by("id")
                    photo = matching_photos.first()
                    caption = f"{view.title()} - temporary low-resolution placeholder"
                    if photo is None:
                        HousePhoto.objects.create(
                            house=house,
                            image=image_name,
                            caption=caption,
                        )
                        created += 1
                    else:
                        matching_photos.exclude(pk=photo.pk).delete()
                        if photo.caption != caption:
                            photo.caption = caption
                            photo.save(update_fields=["caption"])
                        skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Attached {created} placeholder photos across {len(DEMO_APARTMENTS)} properties; "
            f"skipped {skipped} photos already attached."
        ))
