from typing import Optional

import paho.mqtt.client as mqtt
from django.db.models.query import QuerySet


def publish_status(client: mqtt.Client, topic: str, message: str) -> None:
    if topic and message is not None:
        client.publish(topic, message, qos=0, retain=False)


def phase_attribute(phase_index: str, suffix: str) -> Optional[str]:
    mapping = {"1": "r_", "2": "y_", "3": "b_"}
    prefix = mapping.get(str(phase_index))
    if not prefix:
        return None
    return f"{prefix}{suffix}"


def update_phase_entry(entry_qs: QuerySet, phase_index: str, suffix: str, payload: str) -> Optional[float]:
    field = phase_attribute(phase_index, suffix)
    if field is None:
        return None
    try:
        value = float(payload)
    except (TypeError, ValueError):
        return None
    entry_qs.update(**{field: value})
    return value


# Simple process-level caching helpers for common singletons to avoid repeated DB hits
_cached_default_site_id: Optional[int] = None
_cached_home_gateway_id: Optional[str] = None


def get_default_site_id() -> Optional[int]:
    """Return the first Site id, cached for the process lifetime.

    Returns None if no Site exists.
    """
    global _cached_default_site_id
    if _cached_default_site_id is not None:
        return _cached_default_site_id
    try:
        from wareApp.models import Site

        site = Site.objects.first()
        if site:
            _cached_default_site_id = site.id
            return _cached_default_site_id
    except Exception:
        return None
    return None


def get_home_gateway_hgw_id() -> Optional[str]:
    """Return the first HomeGatewayId.hgw_id string, cached for the process lifetime."""
    global _cached_home_gateway_id
    if _cached_home_gateway_id is not None:
        return _cached_home_gateway_id
    try:
        from wareApp.models import HomeGatewayId

        gw = HomeGatewayId.objects.first()
        if gw:
            _cached_home_gateway_id = gw.hgw_id
            return _cached_home_gateway_id
    except Exception:
        return None
    return None
