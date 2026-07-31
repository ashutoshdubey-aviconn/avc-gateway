"""
Module mqtt.topic_parser

Flow:
Top-level functions:
- normalize_payload: Return a UTF-8 string for the payload, with graceful fallbacks.
- parse_mqtt_topic: Parse a slash-separated MQTT topic into a small dict of useful fields.
Top-level classes:
- ParsedTopic
"""

from typing import List, Optional, TypedDict


class ParsedTopic(TypedDict, total=False):
    parts: List[str]
    location_id: Optional[int]
    message_for: Optional[str]
    msg_subtype: Optional[str]
    msg_type: List[str]


def normalize_payload(payload: bytes | bytearray | str | object) -> str:
    """Return a UTF-8 string for the payload, with graceful fallbacks.

    Accepts bytes/bytearray, memoryview, None and arbitrary objects.
    """
    if payload is None:
        return ""
    if isinstance(payload, (bytes, bytearray)):
        try:
            return payload.decode("utf-8", errors="replace")
        except Exception:
            return payload.decode("latin-1", errors="replace")
    # memoryview support
    try:
        if isinstance(payload, memoryview):
            return payload.tobytes().decode("utf-8", errors="replace")
    except Exception:
        pass
    return str(payload)


def parse_mqtt_topic(topic: str) -> ParsedTopic:
    """Parse a slash-separated MQTT topic into a small dict of useful fields.

    Rules (robust):
    - trims leading/trailing slashes
    - parts is the list of path segments
    - location_id: first numeric segment at index 2 or 3 (if present)
    - message_for: segment at index 6 if available
    - msg_type: message_for split by underscore, or empty list
    - msg_subtype: segment at index 7 if available
    """
    if topic is None:
        return {"parts": [], "msg_type": []}

    t = topic.strip().strip("/")
    if not t:
        return {"parts": [], "msg_type": []}

    parts = t.split("/")
    parsed: ParsedTopic = {"parts": parts, "msg_type": []}

    # try common positions for numeric location id
    loc_id: Optional[int] = None
    for idx in (3, 2):
        if len(parts) > idx and parts[idx].isdigit():
            try:
                loc_id = int(parts[idx])
            except Exception:
                loc_id = None
            break
    parsed["location_id"] = loc_id

    # message_for is commonly at index 5 (e.g. the resource/topic name)
    if len(parts) > 5:
        parsed["message_for"] = parts[5]
    # msg_type (the underscore-separated type) is commonly at index 6
    if len(parts) > 6:
        parsed["msg_type"] = parts[6].split("_") if parts[6] else []
        # also expose the raw subtype string from the same segment for tests
        parsed["msg_subtype"] = parts[6]
    else:
        parsed["msg_type"] = []
    # if an additional segment exists after msg_type, keep it as `extra`
    if len(parts) > 7:
        parsed.setdefault("extra", parts[7])

    return parsed
