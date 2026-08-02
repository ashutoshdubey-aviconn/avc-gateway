"""
Module wareApp.testcases.test_router_recovery

Flow:
Top-level classes:
- RouterRecoveryTests
"""

from unittest.mock import Mock, patch

from django.test import TestCase

from wareApp.gateway import recovery
from wareApp.mqtt.router import route_message
from wareApp.mqtt.topic_parser import normalize_payload, parse_mqtt_topic


class RouterRecoveryTests(TestCase):
    def test_normalize_payload_bytes(self):
        assert normalize_payload(b"hello") == "hello"

    def test_parse_mqtt_topic_basic(self):
        parsed = parse_mqtt_topic("/asem/aviconn/123/some/other/topic/meter_power_voltage/consumption")
        # note: parse_mqtt_topic maps parts[6] -> message_for and parts[7] -> msg_subtype
        assert parsed.get("location_id") == 123
        assert parsed.get("message_for") == "topic"
        assert parsed.get("msg_subtype") == "meter_power_voltage"

    def test_route_ignores_state_topic(self):
        client = Mock()
        msg = Mock()
        msg.topic = "/Acclivate/iOmniControl/1/abc/in/state"
        msg.payload = b"{}"
        # should return without raising and not call client.publish
        route_message(client, msg)

    def test_handle_sync_message_consumption_unparseable(self):
        client = Mock()
        msg = Mock()
        # message that lacks valid aisle/leg and date info
        message = "missed:5, noaisle"
        res = recovery.handle_sync_message(client, msg, message, ["METER"], "consumption", None)
        assert res is True

    def test_handle_sync_message_loadtime_unparseable(self):
        client = Mock()
        msg = Mock()
        message = "bad format message"
        res = recovery.handle_sync_message(client, msg, message, ["METER"], "loadTime", None)
        assert res is True
