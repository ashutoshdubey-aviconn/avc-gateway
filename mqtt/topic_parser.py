def normalize_payload(payload):
    if isinstance(payload, bytes):
        try:
            return payload.decode("utf-8", errors="ignore")
        except Exception:
            return payload.decode("latin-1", errors="ignore")
    return str(payload)


def parse_mqtt_topic(topic):
    parts = topic.split("/")
    parsed = {
        "parts": parts,
        "location_id": None,
        "message_for": None,
        "msg_subtype": None,
    }
    if len(parts) > 3 and parts[3].isdigit():
        parsed["location_id"] = int(parts[3])
    if len(parts) > 6:
        parsed["message_for"] = parts[6]
        parsed["msg_type"] = parsed["message_for"].split("_")
    else:
        parsed["msg_type"] = []
    if len(parts) > 7:
        parsed["msg_subtype"] = parts[7]
    return parsed
