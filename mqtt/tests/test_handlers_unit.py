"""
Module mqtt.tests.test_handlers_unit

Flow:
Top-level classes:
- DummyClient
- HandlerUnitTests
"""

from datetime import timezone

from django.test import TestCase


class DummyClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))


class HandlerUnitTests(TestCase):
    def setUp(self):
        from wareApp.models import HomeGatewayId, Site, User

        self.user = User.objects.create(username="handler_tester")
        self.site = Site.objects.create(site_name="unit-site", site_type=1, customer=self.user)
        HomeGatewayId.objects.create(hgw_id="HGW-UNIT")

    def test_handle_source_message_creates_or_updates(self):
        from load.source import handle_source_message
        from wareApp.models import MeterSource, SiteLoadPower

        # create a MeterSource and a matching SiteLoadPower
        MeterSource.objects.create(
            meter_id=1,
            meter_number=0,
            power_source_1=0,
            power_source_2=1,
            meter_type=1,
            is_PS2_valid=False,
            Associated_Site=self.site,
        )
        SiteLoadPower.objects.create(Associated_Site=self.site, Meter_Number=0, Supply_Source="Mains Supply")

        client = DummyClient()
        msg_type = ["SRC", "x", "0", "SOURCE"]
        res = handle_source_message(client, None, self.site, msg_type, "1")
        self.assertTrue(res)
        # Verify SiteLoadPower status updated to ON
        slp = SiteLoadPower.objects.filter(Associated_Site=self.site, Meter_Number=0).first()
        self.assertIsNotNone(slp)
        self.assertEqual(slp.Status, "ON")

    def test_handle_load_time_creates_supply_entry(self):
        from load.runtime import handle_load_time
        from wareApp.models import MeterReadings, MeterSource

        # create meter readings previous value and meter source
        message_for = "meter/topic/1"
        MeterReadings.objects.create(reading_for=1, reading_of=message_for, previous_reading_value="10")
        MeterSource.objects.create(
            meter_id=2,
            meter_number=0,
            power_source_1=1,
            meter_type=1,
            is_PS2_valid=False,
            Associated_Site=self.site,
        )

        client = DummyClient()
        # msg_type must include both 'LOAD' and 'TIME' and index 5 should be '1'
        msg_type = ["METER", "x", "x", "LOAD", "0", "1", "TIME"]
        now = timezone.now()
        res = handle_load_time(client, None, self.site, msg_type, message_for, "20", now)
        self.assertTrue(res)
        # Verify SupplyLoadTimeShare was created with expected hourly_run_time
        from wareApp.models import MeterReadings, SupplyLoadTimeShare

        # load_time = 20 - 10 = 10
        shares = SupplyLoadTimeShare.objects.filter(site=self.site)
        self.assertTrue(shares.exists())
        self.assertAlmostEqual(float(shares.first().hourly_run_time), 10.0, places=3)
        # Verify MeterReadings was updated to new previous_reading_value
        mr = MeterReadings.objects.filter(reading_of=message_for).first()
        self.assertIsNotNone(mr)
        self.assertAlmostEqual(float(mr.previous_reading_value), 20.0, places=3)

    def test_handle_wattage_updates_site_load_power(self):
        from load.wattage import handle_wattage
        from wareApp.models import SiteLoadPower

        SiteLoadPower.objects.create(Associated_Site=self.site, Meter_Number=0, Status="ON")
        msg_type = ["", "", "", "0", "WATTAGE"]
        client = DummyClient()
        res = handle_wattage(client, None, msg_type, "123.4")
        self.assertTrue(res)
        updated = SiteLoadPower.objects.filter(Associated_Site=self.site, Meter_Number=0).first()
        self.assertEqual(float(updated.Site_Total_Load), 123.4)

    def test_handle_wattage_load_publishes(self):
        from load.wattage import handle_wattage_load
        from wareApp.models import LoadData

        LoadData.objects.create(Associated_Site=self.site, Meter_Number=0, leg_id=7)
        msg_type = ["", "", "", "0", "WATTAGELOAD"]
        client = DummyClient()
        res = handle_wattage_load(client, None, msg_type, "55.5")
        self.assertTrue(res)
        # ensure publish was called (since load_power > 0)
        self.assertTrue(len(client.published) >= 1)
        # Verify LoadData row updated
        ld = LoadData.objects.filter(Associated_Site=self.site, Meter_Number=0).first()
        self.assertIsNotNone(ld)
        self.assertAlmostEqual(float(ld.site_total_load), 55.5, places=3)
        self.assertIsNotNone(ld.Updated_on)
        self.assertIsNotNone(ld.epochTime)

    def test_handle_apparent_updates_meter_readings_and_hourly(self):
        from energy.apparent_enery import handle_apparent
        from wareApp.models import AisleGroup, MeterReadings, SmartEnergyDevices

        message_for = "device/topic/9"
        SmartEnergyDevices.objects.create(topic=message_for, leg_id=9, associated_site=self.site)
        AisleGroup.objects.create(site=self.site, aisle_grp_id=9)
        MeterReadings.objects.create(reading_for=0, reading_of=message_for, previous_reading_value="10")

        client = DummyClient()
        now = timezone.now()
        msg_type = ["METER", "x", "x", "x", "0", "APPARENT"]
        res = handle_apparent(client, None, message_for, msg_type, self.site, now, "20", str(self.site.id))
        self.assertTrue(res)
        # Verify HourlySiteReading created and MeterReadings/AisleGroup updated
        from wareApp.models import AisleGroup, HourlySiteReading, MeterReadings

        hourly = HourlySiteReading.objects.filter(associated_Site=self.site, leg_id=9)
        self.assertTrue(hourly.exists())
        # new_unit_consumption = (20 - 10) / 1000 = 0.01
        self.assertAlmostEqual(float(hourly.first().unit_consumption), 0.01, places=6)
        mr = MeterReadings.objects.filter(reading_of=message_for).first()
        self.assertIsNotNone(mr)
        self.assertAlmostEqual(float(mr.previous_reading_value), 20.0, places=3)
        aisle = AisleGroup.objects.filter(site=self.site, aisle_grp_id=9).first()
        self.assertIsNotNone(aisle)
        self.assertAlmostEqual(float(aisle.cumulative_consumption), 0.01, places=6)
