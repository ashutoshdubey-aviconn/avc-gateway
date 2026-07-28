from datetime import datetime

from django.test import TestCase

from mqtt.router import route_message
from wareApp.models import Site, User


class DummyMsg:
    def __init__(self, topic, payload=b"payload"):
        self.topic = topic
        self.payload = payload


class RouterTests(TestCase):
    def setUp(self):
        # create a minimal user and site for lookups
        self.user = User.objects.create(username="testuser")
        self.site = Site.objects.create(site_name="test-site", site_type=1, customer=self.user)

    def test_route_message_no_msg_type_returns_quietly(self):
        msg = DummyMsg("a/b/c/1/2/3")
        # Should not raise and simply return None
        result = route_message(None, msg)
        self.assertIsNone(result)

    def test_route_message_with_meter_type_runs_handlers(self):
        # Construct a topic with at least 7 parts where parts[3] == site id and parts[6] contains METER
        topic = f"x/y/z/{self.site.id}/a/b/METER_ABC"
        msg = DummyMsg(topic, payload=b"123")
        # Should not raise; side effects (DB writes) are not asserted here, only that routing completes
        result = route_message(None, msg)
        self.assertIsNone(result)
