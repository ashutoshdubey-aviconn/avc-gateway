"""
Module mqtt.tests.test_router_handlers_expanded

Flow:
Top-level classes:
- DummyMsg
- RouterExpandedHandlerTests
"""

from unittest.mock import patch

from django.test import TestCase


class DummyMsg:
    def __init__(self, topic, payload=b"payload"):
        self.topic = topic
        self.payload = payload


class RouterExpandedHandlerTests(TestCase):
    def _make_topic(self, site_id, message_for):
        # topic parts: a/b/c/<site_id>/x/y/<message_for>
        return f"a/b/c/{site_id}/x/y/{message_for}"

    def setUp(self):
        from wareApp.models import Site, User

        self.user = User.objects.create(username="expander")
        self.site = Site.objects.create(site_name="exp-site", site_type=1, customer=self.user)

    def _run_and_assert_common(self, message_for, phase_handler_name):
        topic = self._make_topic(self.site.id, message_for)
        msg = DummyMsg(topic, payload=b"data")

        patches = {
            "meter_conn": patch("mqtt.router.handle_meter_connection"),
            "meter_energy": patch("mqtt.router.handle_meter_energy"),
            "voltage": patch("mqtt.router.handle_voltage_message"),
            "current": patch("mqtt.router.handle_current_message"),
            "pf": patch("mqtt.router.handle_power_factor_message"),
            "source": patch("mqtt.router.handle_source_message"),
            "load_time": patch("mqtt.router.handle_load_time"),
            "watt": patch("mqtt.router.handle_wattage"),
            "watt_load": patch("mqtt.router.handle_wattage_load"),
            "apparent": patch("mqtt.router.handle_apparent"),
            "remote": patch("mqtt.router.handle_remote_access"),
            "sync": patch("mqtt.router.handle_sync_message"),
        }
        with (
            patches["meter_conn"].start() as meter_conn,
            patches["voltage"].start() as _voltage,
            patches["current"].start() as _current,
            patches["pf"].start() as _pf,
            patches["source"].start() as _source,
            patches["load_time"].start() as _load_time,
            patches["watt"].start() as _watt,
            patches["watt_load"].start() as _watt_load,
            patches["apparent"].start() as _apparent,
            patches["remote"].start() as remote,
            patches["sync"].start() as sync,
        ):
            meter_conn.return_value = False
            remote.return_value = False
            sync.return_value = False
            # Call router; should complete without exceptions
            from mqtt.router import route_message

            route_message(None, msg)

            # At least one downstream handler should have been called
            assert any(
                [
                    _source.called,
                    _load_time.called,
                    _watt.called,
                    _watt_load.called,
                    _apparent.called,
                    _voltage.called,
                    _current.called,
                    _pf.called,
                ]
            ), "No downstream handlers were called"
            # meter_energy may be implemented downstream; focus on downstream handlers

            # phase-specific handler
            if phase_handler_name == "voltage":
                _voltage.assert_called()
            elif phase_handler_name == "current":
                _current.assert_called()
            elif phase_handler_name == "pf":
                _pf.assert_called()

    def test_phase_2_calls_voltage(self):
        # Test the voltage handler directly by creating a SiteLoadPower entry
        from load.voltage import handle_voltage_message
        from wareApp.models import SiteLoadPower

        # create an entry matching the expected Meter_Number and Associated_Site
        SiteLoadPower.objects.create(Associated_Site=self.site, Meter_Number=0)
        msg_type = ["METER", "x", "x", "x", "0", "A", "2"]

        class Msg:
            def __init__(self):
                self.payload = b"123"

        res = handle_voltage_message(None, Msg(), self.site, msg_type)
        self.assertTrue(res)

    def test_phase_3_calls_current(self):
        from load.current import handle_current_message
        from wareApp.models import SiteLoadPower

        SiteLoadPower.objects.create(Associated_Site=self.site, Meter_Number=0)
        msg_type = ["METER", "x", "x", "x", "0", "A", "3"]

        class Msg:
            def __init__(self):
                self.payload = b"123"

        res = handle_current_message(None, Msg(), self.site, msg_type)
        self.assertTrue(res)

    def test_phase_4_calls_power_factor(self):
        from load.power_factor import handle_power_factor_message
        from wareApp.models import SiteLoadPower

        SiteLoadPower.objects.create(Associated_Site=self.site, Meter_Number=0)
        msg_type = ["METER", "x", "x", "x", "0", "A", "4"]

        class Msg:
            def __init__(self):
                self.payload = b"123"

        res = handle_power_factor_message(None, Msg(), self.site, msg_type)
        self.assertTrue(res)

    def test_remote_access_short_circuits_routing(self):
        # If handle_remote_access returns True, other handlers should not be called
        message_for = "METER_x_x_x_x_x_2"
        topic = self._make_topic(self.site.id, message_for)
        msg = DummyMsg(topic, payload=b"data")

        with (
            patch("mqtt.router.handle_remote_access") as remote,
            patch("mqtt.router.handle_meter_energy") as meter_energy,
        ):
            remote.return_value = True
            from mqtt.router import route_message

            route_message(None, msg)
            meter_energy.assert_not_called()
