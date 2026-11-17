
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.migrations.recorder import MigrationRecorder

from plots.models import House


DEMO_APARTMENTS = (
    ('NBI-01', 'Nairobi County', 'Greenview Residences', 'Kilimani', '2-bedroom', 2, 3200, '4.8', 'A fictional two-bedroom example in Kilimani for exploring the Urban Nest listing and date-search experience.'),
    ('NBI-02', 'Nairobi County', 'Skyline Heights', 'Westlands', '1-bedroom', 1, 2500, '4.6', 'This fictional Westlands listing presents a one-bedroom home as a sample of the city apartment catalogue.'),
    ('NBI-03', 'Nairobi County', 'Olive Gardens', 'Lavington', '3-bedroom', 3, 4500, '4.9', 'A demonstration three-bedroom residence in Lavington, included to show how larger homes appear in search.'),
    ('NBI-04', 'Nairobi County', 'Urban Nest Suites', 'Roysambu', 'Bedsitter', 0, 1200, '4.2', 'This fictional Roysambu bedsitter is a compact example for browsing and checking apartment details.'),
    ('NBI-05', 'Nairobi County', 'Palm Court', 'Kileleshwa', '2-bedroom', 2, 3500, '4.7', 'A sample two-bedroom Kileleshwa listing with a fictional nightly price for demonstration purposes.'),
    ('NBI-06', 'Nairobi County', 'Sunrise Apartments', 'Kasarani', '1-bedroom', 1, 1750, '4.3', 'This Kasarani one-bedroom entry is fictional and helps demonstrate the neighbourhood search flow.'),
    ('NBI-07', 'Nairobi County', 'The Acacia Homes', 'South B', '2-bedroom', 2, 3000, '4.5', 'A fictional South B two-bedroom example, prepared for browsing rather than representing a real rental offer.'),
    ('NBI-08', 'Nairobi County', 'Cedar Point', 'Ruaka Road', 'Studio', 0, 1500, '4.1', 'This demonstration studio is listed around Ruaka Road to illustrate compact-home results.'),
    ('NBI-09', 'Nairobi County', 'Royal Crest Apartments', 'Parklands', '3-bedroom', 3, 4200, '4.8', 'A fictional three-bedroom Parklands residence for viewing the apartment detail layout.'),
    ('NBI-10', 'Nairobi County', 'Maple Residency', 'Embakasi', '1-bedroom', 1, 1500, '4.0', 'This sample Embakasi one-bedroom listing is fictional and can be used to explore search and pagination.'),
    ('KIA-01', 'Kiambu County', 'Ridgeway Gardens', 'Ruiru', '2-bedroom', 2, 2500, '4.6', 'A fictional Ruiru two-bedroom example included in the Kiambu County demonstration listings.'),
    ('KIA-02', 'Kiambu County', 'The Fern Residence', 'Thindigua', '1-bedroom', 1, 1800, '4.5', 'This sample Thindigua one-bedroom home illustrates how area names appear in apartment results.'),
    ('KIA-03', 'Kiambu County', 'Crystal Homes', 'Kikuyu', '2-bedroom', 2, 2200, '4.4', 'A demonstration two-bedroom listing in Kikuyu; its description and rent are fictional sample data.'),
    ('KIA-04', 'Kiambu County', 'Brookside Villas', 'Ruaka', '3-bedroom', 3, 3500, '4.9', 'This fictional Ruaka three-bedroom residence adds a larger-home example to the Kiambu catalogue.'),
    ('KIA-05', 'Kiambu County', 'Hilltop Apartments', 'Juja', 'Bedsitter', 0, 900, '4.0', 'A Juja bedsitter sample for demonstrating compact rental listings in Kiambu County.'),
    ('KIA-06', 'Kiambu County', 'Acorn Heights', 'Kiambu Town', '1-bedroom', 1, 1600, '4.3', 'This fictional one-bedroom listing in Kiambu Town is provided for interface demonstration only.'),
    ('KIA-07', 'Kiambu County', 'Meadow Park', 'Thika', '2-bedroom', 2, 2000, '4.5', 'A sample Thika two-bedroom apartment for trying location-based search and listing navigation.'),
    ('KIA-08', 'Kiambu County', 'Lavender Suites', 'Kikuyu', 'Studio', 0, 1200, '4.1', 'This Kikuyu studio is a fictional entry showing a second compact-home type in the county.'),
    ('KIA-09', 'Kiambu County', 'Cedar Ridge', 'Tatu City', '2-bedroom', 2, 3200, '4.8', 'A fictional Tatu City two-bedroom example with demonstration pricing for the Urban Nest catalogue.'),
    ('KIA-10', 'Kiambu County', 'Valley View Residences', 'Limuru', '3-bedroom', 3, 3000, '4.6', 'This sample three-bedroom Limuru listing rounds out the Kiambu County demonstration homes.'),
    ('MBA-01', 'Mombasa County', 'Ocean Breeze Apartments', 'Nyali', '2-bedroom', 2, 3200, '4.9', 'A fictional Nyali two-bedroom residence included as a coastal example in the demo catalogue.'),
    ('MBA-02', 'Mombasa County', 'Coral Heights', 'Bamburi', '1-bedroom', 1, 1800, '4.5', 'This sample Bamburi one-bedroom listing is fictional and demonstrates the Mombasa area search.'),
    ('MBA-03', 'Mombasa County', 'Palm Shore Residences', 'Shanzu', '3-bedroom', 3, 4000, '4.8', 'A demonstration three-bedroom Shanzu residence, provided to exercise apartment browsing only.'),
    ('MBA-04', 'Mombasa County', 'Bluewater Suites', 'Mtwapa', 'Studio', 0, 1300, '4.2', 'This fictional Mtwapa studio is a compact-home example in the coastal listing collection.'),
    ('MBA-05', 'Mombasa County', 'Coastal View Homes', 'Kizingo', '2-bedroom', 2, 3000, '4.7', 'A sample Kizingo two-bedroom apartment for displaying county and area details in search results.'),
    ('MBA-06', 'Mombasa County', 'Seaside Court', 'Tudor', '1-bedroom', 1, 1500, '4.3', 'This fictional Tudor one-bedroom entry demonstrates a lower nightly sample price in Mombasa.'),
    ('MBA-07', 'Mombasa County', 'Marina Gardens', 'Nyali', '3-bedroom', 3, 4500, '4.9', 'A fictional three-bedroom Nyali residence included to vary home sizes in the Mombasa examples.'),
    ('MBA-08', 'Mombasa County', 'Bahari Apartments', 'Likoni', 'Bedsitter', 0, 800, '3.9', 'This Likoni bedsitter is a fictional compact listing for testing the apartment discovery interface.'),
    ('MBA-09', 'Mombasa County', 'Sunset Palms', 'Bamburi', '2-bedroom', 2, 2500, '4.4', 'A sample two-bedroom Bamburi home, marked as fictional demonstration data in Urban Nest.'),
    ('MBA-10', 'Mombasa County', 'Ocean Pearl Residence', 'Mkomani', '1-bedroom', 1, 2000, '4.6', 'This fictional Mkomani one-bedroom listing completes the Mombasa County sample group.'),
    ('NAK-01', 'Nakuru County', 'Lakeview Residences', 'Milimani', '2-bedroom', 2, 2500, '4.8', 'A fictional Milimani two-bedroom example for browsing Nakuru County apartment listings.'),
    ('NAK-02', 'Nakuru County', 'Acacia Park', 'Section 58', '1-bedroom', 1, 1500, '4.5', 'This Section 58 one-bedroom listing is sample content for demonstrating the catalogue filters.'),
    ('NAK-03', 'Nakuru County', 'Highland Gardens', 'Naka', '3-bedroom', 3, 3200, '4.7', 'A fictional three-bedroom Naka residence included to show a larger Nakuru home listing.'),
    ('NAK-04', 'Nakuru County', 'Rosewood Suites', 'London Estate', 'Studio', 0, 1000, '4.1', 'This London Estate studio is a fictional compact-home example in the Nakuru set.'),
    ('NAK-05', 'Nakuru County', 'Greenfields Apartments', 'Lanet', '2-bedroom', 2, 2000, '4.4', 'A sample Lanet two-bedroom apartment, clearly identified as fictional demonstration content.'),
    ('NAK-06', 'Nakuru County', 'Mountain View Homes', 'Free Area', '1-bedroom', 1, 1200, '4.2', 'This Free Area one-bedroom listing provides another fictional Nakuru neighbourhood example.'),
    ('NAK-07', 'Nakuru County', 'The Oak Residence', 'Kiamunyi', '3-bedroom', 3, 3000, '4.6', 'A fictional three-bedroom Kiamunyi home for exploring property details and date availability.'),
    ('NAK-08', 'Nakuru County', 'Silverstone Court', 'Pipeline', 'Bedsitter', 0, 800, '4.0', 'This Pipeline bedsitter is a compact demonstration listing, not a real rental offer.'),
    ('NAK-09', 'Nakuru County', 'Sunrise Gardens', 'Ngata', '2-bedroom', 2, 1750, '4.3', 'A sample two-bedroom Ngata entry for trying location searches in the Nakuru collection.'),
    ('NAK-10', 'Nakuru County', 'Cedar Valley Homes', 'Milimani', '1-bedroom', 1, 1500, '4.7', 'This fictional Milimani one-bedroom listing completes the Nakuru County demonstration group.'),
    ('MAC-01', 'Machakos County', 'Savannah Heights', 'Athi River', '2-bedroom', 2, 2500, '4.6', 'A fictional Athi River two-bedroom listing for exploring the Machakos County catalogue.'),
    ('MAC-02', 'Machakos County', 'Suncrest Apartments', 'Syokimau', '1-bedroom', 1, 2000, '4.5', 'This Syokimau one-bedroom entry is sample content for testing the listing and search experience.'),
    ('MAC-03', 'Machakos County', 'Acacia Ridge', 'Mlolongo', 'Bedsitter', 0, 1000, '4.0', 'A fictional Mlolongo bedsitter added to demonstrate compact apartment types.'),
    ('MAC-04', 'Machakos County', 'Greenstone Villas', 'Machakos Town', '3-bedroom', 3, 3200, '4.8', 'This sample three-bedroom home in Machakos Town is fictional demonstration data.'),
    ('MAC-05', 'Machakos County', 'Valley Gardens', 'Katani', '2-bedroom', 2, 2200, '4.4', 'A fictional Katani two-bedroom listing for exploring location details and nightly sample pricing.'),
    ('MAC-06', 'Machakos County', 'Crystal Springs', 'Syokimau', 'Studio', 0, 1500, '4.2', 'This Syokimau studio gives the Machakos collection a second compact-home example.'),
    ('MAC-07', 'Machakos County', 'Horizon Residences', 'Athi River', '1-bedroom', 1, 1750, '4.3', 'A sample Athi River one-bedroom residence, clearly marked as fictional for demo use.'),
    ('MAC-08', 'Machakos County', 'Royal Palm Court', 'Machakos Town', '2-bedroom', 2, 2500, '4.5', "This fictional two-bedroom Machakos Town listing rounds out the county's sample locations."),
    ('MAC-09', 'Machakos County', 'Maplewood Apartments', 'Mlolongo', '3-bedroom', 3, 3500, '4.6', 'A fictional three-bedroom Mlolongo example for browsing the Machakos apartment results.'),
    ('MAC-10', 'Machakos County', 'Sunrise Court', 'Kangundo Road', '1-bedroom', 1, 1200, '4.1', 'This Kangundo Road one-bedroom sample completes the 50 fictional demonstration listings.'),
)

MIGRATION_REQUIRED = "0006_announcement_is_published_announcement_recipients_and_more"
ADVISORY_LOCK_SQL = "SELECT pg_advisory_xact_lock(174985042, 52050)"


def marker_for(apartment):
    identifier, _county, _name, _area, property_type, _bedrooms, nightly_price, rating, _description = apartment
    return (
        f"[[URBAN_NEST_DEMO|ID={identifier}|NIGHTLY={nightly_price}|"
        f"TYPE={property_type}|RATING={rating}]]"
    )


class Command(BaseCommand):
    help = "Create fictional demo apartments and refresh prices for existing demo listings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report demo listing changes without writing any records.",
        )

    def _require_current_house_schema(self):
        applied = MigrationRecorder(connection).applied_migrations()
        if ("plots", MIGRATION_REQUIRED) not in applied:
            raise CommandError(
                f"Migration {MIGRATION_REQUIRED} is not applied. "
                "No demo listings were written; apply the reviewed migration first."
            )

        with connection.cursor() as cursor:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(cursor, House._meta.db_table)
            }

        if "is_active" not in columns:
            raise CommandError(
                f"{House._meta.db_table}.is_active is missing despite the migration record. "
                "No demo listings were written; investigate the schema mismatch first."
            )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if not dry_run:
            self._require_current_house_schema()

        created = 0
        skipped = 0
        would_create = 0
        updated = 0
        would_update = 0
        approved = 0
        would_approve = 0

        def seed_missing():
            nonlocal created, skipped, would_create
            nonlocal updated, would_update, approved, would_approve

            for apartment in DEMO_APARTMENTS:
                (
                    identifier, county, name, area, property_type,
                    bedrooms, nightly_price, rating, description
                ) = apartment

                marker = marker_for(apartment)

                existing = House.objects.filter(
                    description__startswith=f"[[URBAN_NEST_DEMO|ID={identifier}|"
                ).first()

                if existing:
                    marker_end = existing.description.find("]]")
                    updated_description = (
                        f"{marker}{existing.description[marker_end + 2:]}"
                        if marker_end >= 0
                        else existing.description
                    )

                    price = Decimal(nightly_price)
                    needs_update = (
                        existing.price_per_night != price
                        or existing.description != updated_description
                    )
                    needs_approval = existing.approval_status != "approved"

                    if dry_run:
                        if needs_update:
                            would_update += 1
                        if needs_approval:
                            would_approve += 1
                    else:
                        changed_fields = []

                        if needs_update:
                            existing.price_per_night = price
                            existing.description = updated_description
                            changed_fields.extend(["price_per_night", "description"])
                            updated += 1

                        if needs_approval:
                            existing.approval_status = "approved"
                            changed_fields.append("approval_status")
                            approved += 1

                        if changed_fields:
                            existing.save(update_fields=changed_fields)

                    if not needs_update and not needs_approval:
                        skipped += 1

                    continue

                if dry_run:
                    would_create += 1
                    continue

                House.objects.create(
                    name=name,
                    location=f"{county} - {area}",
                    description=f"{marker} Fictional demonstration listing. {description}",
                    bedrooms=bedrooms,
                    price_per_night=Decimal(nightly_price),
                    is_active=True,
                    approval_status="approved",
                )
                created += 1

        if dry_run:
            seed_missing()
            self.stdout.write(
                f"Dry run complete: {would_create} would be created; "
                f"{would_update} would be updated; "
                f"{would_approve} existing demo listings would be approved; "
                f"{skipped} already current; no records changed."
            )
        else:
            with transaction.atomic():
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute(ADVISORY_LOCK_SQL)

                seed_missing()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Created {created} demo apartments; "
                    f"updated {updated} demo listings; "
                    f"approved {approved} existing demo listings; "
                    f"skipped {skipped} unchanged."
                )
            )

        self.stdout.write(
            "Only listings identified by the URBAN_NEST_DEMO markers were updated. "
            "Customer-submitted properties were not approved or modified."
        )
