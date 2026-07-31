"""
Module mqtt.tests.test_recovery

Flow:
Top-level classes:
- DummyClient
- RecoveryHandlerTests
"""

from datetime import datetime, timedelta

from django.test import TestCase
from django.utils import timezone


class DummyClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))


class RecoveryHandlerTests(TestCase):
    def setUp(self):
        from wareApp.models import HomeGatewayId, Site, User

        self.user = User.objects.create(username="recovery_tester")
        self.site = Site.objects.create(site_name="rec-site", site_type=1, customer=self.user)
        HomeGatewayId.objects.create(hgw_id="HGW-REC")

    def test_consumption_recovery_publishes_daily_and_hourly(self):
        from gateway.recovery import handle_sync_message
        from wareApp.models import AisleGroup, DailySiteReading, HourlySiteReading

        # create aisle group and readings for a two-day range
        aisle = AisleGroup.objects.create(site=self.site, aisle_grp_id=1, cumulative_consumption=42.0)
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)

        DailySiteReading.objects.create(
            associated_Site=self.site,
            aisle_group=aisle,
            leg_id=1,
            unit_consumption=1.5,
            reading_for=yesterday,
        )
        # hourly entry for yesterday at hour 0
        hour_from = datetime.combine(yesterday, datetime.min.time())
        HourlySiteReading.objects.create(
            associated_Site=self.site,
            aisle_group=aisle,
            leg_id=1,
            unit_consumption=0.25,
            reading_from=hour_from,
            reading_to=hour_from + timedelta(hours=1),
        )

        client = DummyClient()
        # message: missed token, aisle id, start date and end date
        msg = "missed:0,aisle:1,{start},{end}".format(
            start=yesterday.strftime("%Y-%m-%d"), end=today.strftime("%Y-%m-%d")
        )
        res = handle_sync_message(
            client,
            None,
            msg,
            ["SYNC"],
            "consumption",
            self.site,
            datetime.combine(today, datetime.min.time()),
        )
        self.assertTrue(res)
        # ensure at least one daily and one hourly publish occurred
        topics = [t for (t, p, q, r) in client.published]
        self.assertTrue(any("dailyConsumption" in t for t in topics))
        self.assertTrue(any("hourlyConsumption" in t for t in topics))

    def test_loadtime_recovery_publishes_loadRuntime(self):
        from gateway.recovery import handle_sync_message
        from wareApp.models import SupplyLoadTimeShare

        # create a supply entry with readings that cover the last synced hour
        reading_from = timezone.now() - timedelta(hours=2)
        reading_to = timezone.now() + timedelta(hours=2)
        SupplyLoadTimeShare.objects.create(
            site=self.site,
            power_source=1,
            hourly_run_time=30,
            reading_from=reading_from,
            reading_to=reading_to,
        )

        client = DummyClient()
        sync_hour = (timezone.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S.%f")
        msg = f"Power_source : 1, Missed_consumption_time_in_secs : 3600, Last_synced_hour : {sync_hour}"
        res = handle_sync_message(client, None, msg, ["SYNC"], "loadTime", self.site, timezone.now())
        self.assertTrue(res)
        # should have published a loadRuntime recovery message
        topics = [t for (t, p, q, r) in client.published]
        self.assertTrue(any("loadRuntime" in t for t in topics))
