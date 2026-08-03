"""
Module wareApp.migrations.0003_backfill_index_fields

Flow:
Top-level functions:
- forwards
- reverse
Top-level classes:
- Migration
"""

from django.db import migrations


def forwards(apps, schema_editor):
    AisleGroup = apps.get_model("wareApp", "AisleGroup")
    DailySiteReading = apps.get_model("wareApp", "DailySiteReading")
    HourlySiteReading = apps.get_model("wareApp", "HourlySiteReading")

    # Backfill aisle_grp_id to 0 where missing
    AisleGroup.objects.filter(aisle_grp_id__isnull=True).update(aisle_grp_id=0)

    # Backfill leg_id in daily/hourly readings to 'UNKNOWN' where missing or empty
    DailySiteReading.objects.filter(leg_id__isnull=True).update(leg_id="UNKNOWN")
    DailySiteReading.objects.filter(leg_id__exact="").update(leg_id="UNKNOWN")

    HourlySiteReading.objects.filter(leg_id__isnull=True).update(leg_id="UNKNOWN")
    HourlySiteReading.objects.filter(leg_id__exact="").update(leg_id="UNKNOWN")

    # Ensure reading_from/reading_to are set to a sane value if missing
    from django.utils import timezone

    now = timezone.now()
    HourlySiteReading.objects.filter(reading_from__isnull=True).update(reading_from=now)
    HourlySiteReading.objects.filter(reading_to__isnull=True).update(reading_to=now)


def reverse(apps, schema_editor):
    # No-op reverse; do not clear data
    pass


class Migration(migrations.Migration):
    dependencies = [("wareApp", "0002_add_indexes")]

    operations = [migrations.RunPython(forwards, reverse)]
