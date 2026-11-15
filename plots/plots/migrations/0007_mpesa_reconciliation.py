from django.db import migrations, models
from django.db.models import Q


def mark_unresolved_attempts_uncertain(apps, schema_editor):
    MpesaPayment = apps.get_model("plots", "MpesaPayment")
    MpesaPayment.objects.filter(status="failed").filter(
        Q(checkout_request_id__isnull=True) | Q(checkout_request_id="")
    ).exclude(result_description__istartswith="OAuth token retrieval").exclude(
        result_description__istartswith="STK Push was rejected"
    ).update(status="uncertain")


def restore_uncertain_attempts(apps, schema_editor):
    MpesaPayment = apps.get_model("plots", "MpesaPayment")
    MpesaPayment.objects.filter(status="uncertain").filter(
        Q(checkout_request_id__isnull=True) | Q(checkout_request_id="")
    ).update(status="failed")


class Migration(migrations.Migration):
    dependencies = [
        ("plots", "0006_announcement_is_published_announcement_recipients_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="mpesapayment",
            name="stk_response",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="mpesapayment",
            name="query_response",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="mpesapayment",
            name="callback_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="mpesapayment",
            name="last_query_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="mpesapayment",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("success", "Success"),
                    ("failed", "Failed"),
                    ("cancelled", "Cancelled"),
                    ("uncertain", "Uncertain outcome"),
                    ("review", "Needs review"),
                ],
                db_index=True,
                default="pending",
                max_length=10,
            ),
        ),
        migrations.RunPython(mark_unresolved_attempts_uncertain, restore_uncertain_attempts),
    ]
