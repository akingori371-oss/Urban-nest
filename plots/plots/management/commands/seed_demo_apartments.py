
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from plots.models import House


# Existing database IDs for the five properties to retain per county.
# These are the first five properties in each county.
KEEP_IDS = {
    1, 2, 3, 4, 5,          # Nairobi
    11, 12, 13, 14, 15,     # Kiambu
    21, 22, 23, 24, 25,     # Mombasa
    31, 32, 33, 34, 35,     # Nakuru
    41, 42, 43, 44, 45,     # Machakos
}

# Existing database IDs for all 50 original catalogue properties.
ORIGINAL_IDS = set(range(1, 51))


class Command(BaseCommand):
    help = "Maintain the original 25-property Urban Nest catalogue."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without modifying the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        properties = House.objects.filter(id__in=ORIGINAL_IDS)

        found_ids = set(properties.values_list("id", flat=True))
        missing_ids = ORIGINAL_IDS - found_ids

        if missing_ids:
            raise CommandError(
                f"Expected original property records are missing: "
                f"{sorted(missing_ids)}. No changes made."
            )

        to_keep = properties.filter(id__in=KEEP_IDS)
        to_deactivate = properties.exclude(id__in=KEEP_IDS)

        self.stdout.write(
            f"Properties to retain: {to_keep.count()}"
        )
        self.stdout.write(
            f"Properties to deactivate: {to_deactivate.count()}"
        )

        # Preview the affected records.
        for house in to_deactivate.order_by("id"):
            self.stdout.write(
                f"Would deactivate ID {house.id}: {house.name}"
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "Dry run complete. No database records were changed."
                )
            )
            return

        with transaction.atomic():
            # Keep the selected 25 active.
            to_keep.update(is_active=True)

            # Retire the other 25 without deleting their records.
            to_deactivate.update(is_active=False)

        self.stdout.write(
            self.style.SUCCESS(
                "Catalogue updated successfully. "
                "25 original properties retained and 25 deactivated."
            )
        )
