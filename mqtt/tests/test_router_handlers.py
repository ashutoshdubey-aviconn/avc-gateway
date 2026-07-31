"""
Module mqtt.tests.test_router_handlers

Flow:
Top-level classes:
- DummyMsg
- RouterHandlerInvocationTests
"""

from unittest.mock import patch

from django.test import TestCase

from mqtt.router import route_message


class DummyMsg:
    def __init__(self, topic, payload=b"payload"):
        self.topic = topic
        self.payload = payload


class RouterHandlerInvocationTests(TestCase):
    def test_handlers_called_for_meter_topic(self):
        # topic parts: /x/y/<site_id>/a/b/METER_ABC
        # Create message with METER in the msg_type to trigger handlers
        from wareApp.models import Site, User

        user = User.objects.create(username="tester")
        site = Site.objects.create(site_name="s1", site_type=1, customer=user)
        site_id = site.id
        topic = f"x/y/z/{site_id}/a/b/METER_ABC"
        msg = DummyMsg(topic, payload=b"123")

        with patch("mqtt.router.handle_meter_connection") as meter_conn, patch(
            "mqtt.router.handle_meter_energy"
        ) as meter_energy:
            # Configure return for meter connection to False so flow continues
            meter_conn.return_value = False

            # Call router; should not raise
            result = route_message(None, msg)
            self.assertIsNone(result)

            # At least ensure meter_energy was invoked (others may be conditional)
            meter_energy.assert_called()
