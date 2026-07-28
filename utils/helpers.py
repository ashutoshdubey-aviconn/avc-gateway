from typing import Any, Optional


def publish_status(client: Any, topic: str, message: str) -> None:
    if topic and message is not None:
        client.publish(topic, message, qos=0, retain=False)


def phase_attribute(phase_index: str, suffix: str) -> Optional[str]:
    mapping = {"1": "r_", "2": "y_", "3": "b_"}
    prefix = mapping.get(str(phase_index))
    if not prefix:
        return None
    return f"{prefix}{suffix}"


def update_phase_entry(entry_qs: Any, phase_index: str, suffix: str, payload: Any) -> Optional[float]:
    field = phase_attribute(phase_index, suffix)
    if field is None:
        return None
    try:
        value = float(payload)
    except (TypeError, ValueError):
        return None
    entry_qs.update(**{field: value})
    return value
