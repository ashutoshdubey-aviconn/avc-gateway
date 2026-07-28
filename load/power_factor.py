import logging

from utils.helpers import update_phase_entry
from wareApp.models import SiteLoadPower

logger = logging.getLogger(__name__)


from typing import Any


def _handle_phase(client: Any, msg: Any, site: Any, msg_type: Any, suffix: str, required_code: str) -> bool:
    if len(msg_type) <= 6 or msg_type[6] != required_code:
        return False
    entry = SiteLoadPower.objects.filter(
        Associated_Site=site,
        Meter_Number=int(msg_type[4]) if len(msg_type) > 4 else 0,
    )
    if not entry.exists():
        return True
    updated = update_phase_entry(entry, msg_type[5], suffix, msg.payload)
    if updated is not None:
        logger.info("Phase %s %s updated as %s.", msg_type[5], suffix, updated)
    return True


def handle_power_factor_message(client: Any, msg: Any, site: Any, msg_type: Any) -> bool:
    return _handle_phase(client, msg, site, msg_type, "power_factor", "4")
