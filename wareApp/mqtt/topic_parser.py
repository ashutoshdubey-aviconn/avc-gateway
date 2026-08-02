"""
Migrated mqtt.topic_parser
"""

from typing import List, Optional, TypedDict


class ParsedTopic(TypedDict, total=False):
    parts: List[str]
    location_id: Optional[int]
    message_for: Optional[str]
    msg_subtype: Optional[str]
    msg_type: List[str]


def normalize_payload(payload: bytes | bytearray | str | object) -> str:
    if payload is None:
        return ""
    if isinstance(payload, (bytes, bytearray)):
        try:
            return payload.decode("utf-8", errors="replace")
        except Exception:
            return payload.decode("latin-1", errors="replace")
    try:
        if isinstance(payload, memoryview):
            return payload.tobytes().decode("utf-8", errors="replace")
    except Exception:
        pass
    return str(payload)


def parse_mqtt_topic(topic: str) -> ParsedTopic:
    if topic is None:
        return {"parts": [], "msg_type": []}

    t = topic.strip().strip("/")
    if not t:
        return {"parts": [], "msg_type": []}

    parts = t.split("/")
    parsed: ParsedTopic = {"parts": parts, "msg_type": []}

    loc_id: Optional[int] = None
    for idx in (3, 2):
        if len(parts) > idx and parts[idx].isdigit():
            try:
                loc_id = int(parts[idx])
            except Exception:
                loc_id = None
            break
    parsed["location_id"] = loc_id

    if len(parts) > 5:
        parsed["message_for"] = parts[5]

    generic_suffixes = {"localstate", "state", "status", "set", "get"}
    if len(parts) > 6 and parts[6] and parts[6].lower() not in generic_suffixes and "_" in parts[6]:
        parsed["msg_type"] = parts[6].split("_")
        parsed["msg_subtype"] = parts[6]
    elif len(parts) > 5 and "_" in parts[5]:
        parsed["msg_type"] = parts[5].split("_")
        parsed["msg_subtype"] = parts[5]
    else:
        parsed["msg_type"] = []

    if len(parts) > 7:
        parsed.setdefault("extra", parts[7])

    return parsed
