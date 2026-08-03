"""
Copied router handler tests.
"""

from unittest.mock import patch

from django.test import TestCase

from wareApp.mqtt.router import route_message


class DummyMsg:
    def __init__(self, topic, payload=b"payload"):
        self.topic = topic
        self.payload = payload


class RouterHandlerInvocationTests(TestCase):
    def test_handlers_called_for_meter_topic(self):
        from wareApp.models import Site, User

        user = User.objects.create(username="tester")
        site = Site.objects.create(site_name="s1", site_type=1, customer=user)
        site_id = site.id
        topic = f"x/y/z/{site_id}/a/b/METER_ABC"
        msg = DummyMsg(topic, payload=b"123")

        with patch("wareApp.mqtt.router.handle_meter_connection") as meter_conn, patch(
            "wareApp.mqtt.router.handle_meter_energy"
        ) as meter_energy:
            meter_conn.return_value = False
            result = route_message(None, msg)
            self.assertIsNone(result)
            meter_energy.assert_called()
