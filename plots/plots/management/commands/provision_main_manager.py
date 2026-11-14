import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.utils import timezone

from plots.models import ManagerInvitation, ManagerProfile


MAIN_EMAIL = "akingori371@gmail.com"


class Command(BaseCommand):
    help = "Email a single-use verification invitation to the configured initial Urban Nest main manager."

    def handle(self, *args, **options):
        mail_backend = settings.MAILERS.get("default", {}).get("BACKEND", "")
        if mail_backend.endswith("console.EmailBackend") or mail_backend.endswith("locmem.EmailBackend"):
            raise CommandError("Configure a secure delivery email backend before provisioning the main manager.")
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
            send_mail("Verify your Urban Nest main manager account",
                      f"Sign in to the Urban Nest account for {MAIN_EMAIL}, then open this single-use link to verify ownership and activate main-manager access:\n\n{link}\n\nThis link expires in 7 days.",
                      settings.DEFAULT_FROM_EMAIL, [MAIN_EMAIL], fail_silently=False)
        except Exception as exc:
            invitation.delete()
            raise CommandError("Could not send the verification email. Check the configured email settings.") from exc
        self.stdout.write(self.style.SUCCESS(f"Verification email sent to {MAIN_EMAIL}. No privileges were granted yet."))
