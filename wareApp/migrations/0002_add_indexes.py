"""
Module wareApp.migrations.0002_add_indexes

Flow:
Top-level classes:
- Migration
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("wareApp", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="aislegroup",
            index=models.Index(fields=["site_id", "aisle_grp_id"], name="wa_aisle_site_grp_idx"),
        ),
        migrations.AddIndex(
            model_name="aislegroup",
            index=models.Index(fields=["aisle_grp_id"], name="wa_aisle_grp_id_idx"),
        ),
        migrations.AddIndex(
            model_name="dailysitereading",
            index=models.Index(fields=["leg_id", "reading_for"], name="wa_daily_leg_reading_idx"),
        ),
        migrations.AddIndex(
            model_name="hourlysitereading",
            index=models.Index(fields=["leg_id", "reading_from", "reading_to"], name="wa_hourly_leg_from_to_idx"),
        ),
    ]
