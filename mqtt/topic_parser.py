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

    # msg_type is commonly at index 6. However some publishers place the
    # underscore-separated resource token at index 5 (e.g.
    # `/.../out/METER_.../localstate`). If index 6 exists but is a generic
    # suffix like 'localstate' we should prefer the resource at index 5.
    generic_suffixes = {"localstate", "state", "status", "set", "get"}
    if len(parts) > 6 and parts[6] and parts[6].lower() not in generic_suffixes and "_" in parts[6]:
        # e.g. parts[6] == 'TOTAL_LOAD_WATTAGE_1'
        parsed["msg_type"] = parts[6].split("_")
        parsed["msg_subtype"] = parts[6]
    elif len(parts) > 5 and "_" in parts[5]:
        # e.g. parts[5] == 'METER_132_GF_L14_2_1_1'
        parsed["msg_type"] = parts[5].split("_")
        parsed["msg_subtype"] = parts[5]
    else:
        parsed["msg_type"] = []
    # if an additional segment exists after msg_type, keep it as `extra`
    if len(parts) > 7:
        parsed.setdefault("extra", parts[7])

    return parsed
