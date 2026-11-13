from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("plots", "0003_mpesapayment")]

    operations = [
        migrations.AlterField(
            model_name="mpesapayment",
            name="checkout_request_id",
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
        migrations.CreateModel(
            name="MpesaCallbackEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("checkout_request_id", models.CharField(max_length=100, unique=True)),
                ("payload", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.AddConstraint(
            model_name="paymentperiod",
            constraint=models.UniqueConstraint(fields=("booking", "number"), name="unique_booking_period_number"),
        ),
        migrations.AddConstraint(
            model_name="mpesapayment",
            constraint=models.CheckConstraint(
                condition=(models.Q(("booking__isnull", False), ("period__isnull", True))
                           | models.Q(("booking__isnull", True), ("period__isnull", False))),
                name="mpesa_payment_exactly_one_target",
            ),
        ),
    ]
