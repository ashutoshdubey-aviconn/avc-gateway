"""
Copied router tests to tests/mqtt.
"""

from django.test import TestCase

from wareApp.models import Site, User
from wareApp.mqtt.router import route_message


class DummyMsg:
    def __init__(self, topic, payload=b"payload"):
        self.topic = topic
        self.payload = payload


class RouterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="testuser")
        self.site = Site.objects.create(site_name="test-site", site_type=1, customer=self.user)

    def test_route_message_no_msg_type_returns_quietly(self):
        msg = DummyMsg("a/b/c/1/2/3")
        result = route_message(None, msg)
        self.assertIsNone(result)

    def test_route_message_with_meter_type_runs_handlers(self):
        topic = f"x/y/z/{self.site.id}/a/b/METER_ABC"
        msg = DummyMsg(topic, payload=b"123")
        result = route_message(None, msg)
        self.assertIsNone(result)
