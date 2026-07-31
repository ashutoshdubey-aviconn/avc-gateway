"""
Module wareApp.testcases.test_backfill

Flow:
Top-level classes:
- BackfillTests
"""

from django.test import TestCase
from django.utils import timezone

from wareApp.models import AisleGroup, DailySiteReading, HourlySiteReading, Site


class BackfillTests(TestCase):
    def test_backfill_index_fields(self):
        site = Site.objects.create(site_name="test-site")

        # Create records with NULL/empty values
        a1 = AisleGroup.objects.create(site=site, aisle_grp_id=None, aisleGroupName="g1")
        DailySiteReading.objects.create(associated_Site=site, aisle_group=a1, leg_id=None, unit_consumption=1.2)
        HourlySiteReading.objects.create(associated_Site=site, aisle_group=a1, leg_id="", unit_consumption=3.4)

        # Simulate the backfill migration logic
        AisleGroup.objects.filter(aisle_grp_id__isnull=True).update(aisle_grp_id=0)
        DailySiteReading.objects.filter(leg_id__isnull=True).update(leg_id="UNKNOWN")
        DailySiteReading.objects.filter(leg_id__exact="").update(leg_id="UNKNOWN")
        HourlySiteReading.objects.filter(leg_id__isnull=True).update(leg_id="UNKNOWN")
        HourlySiteReading.objects.filter(leg_id__exact="").update(leg_id="UNKNOWN")
        now = timezone.now()
        HourlySiteReading.objects.filter(reading_from__isnull=True).update(reading_from=now)
        HourlySiteReading.objects.filter(reading_to__isnull=True).update(reading_to=now)

        # Refresh from DB and assert
        a1.refresh_from_db()
        self.assertIsNotNone(a1.aisle_grp_id)
        self.assertEqual(a1.aisle_grp_id, 0)

        dr = DailySiteReading.objects.first()
        self.assertIsNotNone(dr.leg_id)
        self.assertNotEqual(dr.leg_id, "")

        hr = HourlySiteReading.objects.first()
        self.assertIsNotNone(hr.leg_id)
        self.assertNotEqual(hr.leg_id, "")
        self.assertIsNotNone(hr.reading_from)
        self.assertIsNotNone(hr.reading_to)
