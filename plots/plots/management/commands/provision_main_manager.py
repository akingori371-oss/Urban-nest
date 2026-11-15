import hashlib
import os
import secrets
from datetime import timedelta
from email.utils import parseaddr

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from plots.models import ManagerInvitation, ManagerProfile


MAIN_EMAIL = "akingori371@gmail.com"
SMTP_EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


class Command(BaseCommand):
    help = "Provision the initial main manager by invitation or explicitly activate the existing local account."

    def add_arguments(self, parser):
        parser.add_argument(
            "--activate-existing",
            action="store_true",
            help="Activate the existing fixed main-manager account on the local development database without email.",
        )

    def handle(self, *args, **options):
        if options["activate_existing"]:
            self.activate_existing_account()
            return

        if settings.EMAIL_BACKEND != SMTP_EMAIL_BACKEND:
            raise CommandError("Set EMAIL_BACKEND to Django's SMTP backend before provisioning the main manager.")
        if not settings.EMAIL_HOST or not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            raise CommandError("Configure EMAIL_HOST, EMAIL_HOST_USER, and EMAIL_HOST_PASSWORD before provisioning.")
        if settings.EMAIL_USE_TLS == settings.EMAIL_USE_SSL:
            raise CommandError("Enable exactly one of EMAIL_USE_TLS or EMAIL_USE_SSL before provisioning.")
        sender_address = parseaddr(settings.DEFAULT_FROM_EMAIL)[1]
        if not sender_address or sender_address.lower().endswith("@localhost"):
            raise CommandError("Configure DEFAULT_FROM_EMAIL with a verified sender address before provisioning.")

        user = get_user_model().objects.filter(email__iexact=MAIN_EMAIL, is_active=True).first()
        if not user:
            raise CommandError(f"Create an active account for {MAIN_EMAIL} first. The command will not create or promote accounts by email alone.")
        if ManagerProfile.objects.filter(is_main=True).exists():
            self.stdout.write(self.style.SUCCESS("A main manager is already provisioned."))
            return
        pending = ManagerInvitation.objects.filter(email__iexact=MAIN_EMAIL, status="pending", is_main_provision=True, expires_at__gt=timezone.now()).first()
        if pending:
            self.stdout.write("A main-manager verification invitation is already pending.")
            return
        token = secrets.token_urlsafe(48)
        invitation = ManagerInvitation.objects.create(
            email=MAIN_EMAIL,
            token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
            is_main_provision=True,
            expires_at=timezone.now() + timedelta(days=7),
        )
        base = getattr(settings, "URBAN_NEST_FRONTEND_URL", "http://localhost:5173").rstrip("/")
        link = f"{base}/manager/invitations/accept/{token}"
        try:
            delivered = send_mail(
                "Verify your Urban Nest main manager account",
                f"Sign in to the Urban Nest account for {MAIN_EMAIL}, then open this single-use link to verify ownership and activate main-manager access:\n\n{link}\n\nThis link expires in 7 days.",
                settings.DEFAULT_FROM_EMAIL,
                [MAIN_EMAIL],
                fail_silently=False,
            )
            if delivered != 1:
                raise RuntimeError("Email backend did not confirm delivery.")
        except Exception as exc:
            invitation.delete()
            raise CommandError("Could not send the verification email. Check the configured email settings.") from exc
        self.stdout.write(self.style.SUCCESS(f"Verification email sent to {MAIN_EMAIL}. No privileges were granted yet."))

    def activate_existing_account(self):
        database = settings.DATABASES["default"]
        local_hosts = {"localhost", "127.0.0.1", "::1"}
        local_postgres = (
            database["ENGINE"] == "django.db.backends.postgresql"
            and str(database["NAME"]) in {"urban_nest", "test_urban_nest"}
            and str(database["HOST"]).lower() in local_hosts
        )
        isolated_test_database = (
            database["ENGINE"] == "django.db.backends.sqlite3"
            and os.environ.get("DJANGO_SETTINGS_MODULE") == "config.test_settings"
        )
        if not settings.DEBUG or not (local_postgres or isolated_test_database):
            raise CommandError(
                "Direct activation is restricted to local DEBUG urban_nest or the isolated in-memory test database."
            )

        User = get_user_model()
        with transaction.atomic():
            matches = User.objects.select_for_update().filter(email__iexact=MAIN_EMAIL)
            if matches.count() != 1:
                raise CommandError(
                    f"Expected exactly one existing account for {MAIN_EMAIL}; no account was changed."
                )
            user = matches.get()
            if not user.is_active:
                raise CommandError(
                    f"The existing account for {MAIN_EMAIL} is inactive; no account was changed."
                )

            current_main = ManagerProfile.objects.select_for_update().filter(is_main=True).first()
            if current_main and current_main.user_id != user.pk:
                raise CommandError(
                    "A different main manager is already configured; no manager profile was changed."
                )
            ManagerProfile.objects.update_or_create(user=user, defaults={"is_main": True})

        self.stdout.write(self.style.SUCCESS(
            "The existing main-manager account is active. No user, password, invitation, or email was changed."
        ))
