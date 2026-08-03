"""
Migrated constants.topics
"""

BASE_TOPIC_PREFIX = "/Acclivate/iOmniControl"


def build_topic(*parts: object) -> str:
    normalized = [str(part).strip("/") for part in parts if part is not None]
    return "/".join([BASE_TOPIC_PREFIX] + normalized)


def consumption_state_topic(site_id: int, gateway_id: int | str) -> str:
    return build_topic(site_id, gateway_id, "in", "consumption", "state")


def load_state_topic(site_id: int, gateway_id: int | str) -> str:
    return build_topic(site_id, gateway_id, "in", "load", "state")


def supply_time_state_topic(site_id: int, gateway_id: int | str) -> str:
    return build_topic(site_id, gateway_id, "in", "SupplyTime", "state")


def load_data_state_topic(site_id: int, gateway_id: int | str) -> str:
    return build_topic(site_id, gateway_id, "in", "LoadData", "state")


def recovery_daily_consumption_topic(site_id: int, gateway_id: int | str) -> str:
    return build_topic(site_id, gateway_id, "in", "recovery", "dailyConsumption", "state")


def recovery_hourly_consumption_topic(site_id: int, gateway_id: int | str) -> str:
    return build_topic(site_id, gateway_id, "in", "recovery", "hourlyConsumption")


def recovery_load_runtime_topic(site_id: int, gateway_id: int | str) -> str:
    return build_topic(site_id, gateway_id, "in", "recovery", "loadRuntime")


def remote_access_state_topic(connected_to_id: int | str, gateway_id: int | str) -> str:
    return build_topic(connected_to_id, gateway_id, "in", "remoteAccess", "state")
