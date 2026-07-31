#!/usr/bin/env python3
"""Provision local DB with site data fetched from a central server.

The script requests JSON from a server endpoint and upserts Site, AisleGroup,
BlockInfo, Panel, Floor, HomeGatewayId, and SmartEnergyDevices records.

Usage:
  ./venv/bin/python scripts/provision_from_server.py --url https://server/api/sites/164 --site-id 164
  ./venv/bin/python scripts/provision_from_server.py --url https://server/api/sites --all

Expected server JSON (example):
  {
    "site": { "id": 164, "site_name": "office", "location": "office", "site_type": 1, ... },
    "home_gateways": [ {"hgw_id": "id", "rssh_port": "40293", "monitoring_port": "40292"}, ... ],
    "aisle_groups": [ {"aisle_grp_id": 10, "aisleGroupName": "A1", "total_lights": 10, ...}, ... ],
    "blocks": [ {"block_name": "B1", "is_active": true}, ... ],
    "panels": [ {"panel": "P1"}, ... ],
    "floors": [ {"floor": "GF"}, ... ],
    "smart_devices": [ {"topic": "...", "device_type": 1, "leg_id": 5}, ... ]
  }

The script is idempotent and uses update_or_create for safety.
"""

import argparse
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import requests


def setup_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "warehouse.settings")
    import django

    django.setup()


def iso_datetime_or_none(s: Optional[str]):
    from datetime import datetime

    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        try:
            # fallback common format
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None


def upsert_site(data: Dict[str, Any], dry_run: bool = False):
    from wareApp.models import Site

    fields = dict(
        site_name=data.get("site_name") or data.get("name"),
        location=data.get("location"),
        site_type=data.get("site_type"),
        total_no_of_blocks=data.get("total_no_of_blocks"),
        total_no_of_aisles=data.get("total_no_of_aisles"),
        per_unit_cost=data.get("per_unit_cost"),
        genset_unit_rate=data.get("genset_unit_rate"),
        no_of_single_source_meters=data.get("no_of_single_source_meters"),
        no_of_dual_source_meters=data.get("no_of_dual_source_meters"),
        is_active=data.get("is_active", False),
        is_visible=data.get("is_visible", False),
        current_baseline=data.get("current_baseline"),
        consumed_energy=data.get("consumed_energy"),
        total_energy_saved=data.get("total_energy_saved"),
        avg_saving=data.get("avg_saving"),
    )
    if dry_run:
        logging.info("DRY RUN: would upsert Site with pk=%s fields=%s", data.get("id"), fields)
        return None

    site, created = Site.objects.update_or_create(pk=data.get("id"), defaults=fields)
    logging.info("Site upserted: id=%s created=%s", site.id, created)
    return site


def upsert_home_gateways(site_obj, items: List[Dict[str, Any]], dry_run: bool = False):
    from wareApp.models import HomeGatewayId

    for it in items:
        defaults = {
            "connected_to": site_obj,
            "rssh_port": (str(it.get("rssh_port")) if it.get("rssh_port") is not None else None),
            "monitoring_port": (str(it.get("monitoring_port")) if it.get("monitoring_port") is not None else None),
        }
        if dry_run:
            logging.info("DRY RUN: would upsert HomeGateway %s -> %s", it.get("hgw_id"), defaults)
            continue
        obj, created = HomeGatewayId.objects.update_or_create(hgw_id=it.get("hgw_id"), defaults=defaults)
        logging.info("HomeGatewayId upserted: %s created=%s", obj.hgw_id, created)


def upsert_aisle_groups(site_obj, items: List[Dict[str, Any]], dry_run: bool = False):
    from wareApp.models import AisleGroup

    for it in items:
        defaults = {
            "site": site_obj,
            "aisleGroupName": it.get("aisleGroupName") or it.get("name"),
            "total_lights": it.get("total_lights"),
            "one_light_watt": it.get("one_light_watt"),
            "expected_consumption": it.get("expected_consumption"),
            "is_active": it.get("is_active", False),
            "cumulative_consumption": it.get("cumulative_consumption", 0),
            "power_source": it.get("power_source", 0),
        }
        if dry_run:
            logging.info(
                "DRY RUN: would upsert AisleGroup %s -> %s",
                it.get("aisle_grp_id"),
                defaults,
            )
            continue
        obj, created = AisleGroup.objects.update_or_create(
            aisle_grp_id=it.get("aisle_grp_id"), site=site_obj, defaults=defaults
        )
        logging.info("AisleGroup upserted: %s created=%s", obj.id, created)


def upsert_blocks(site_obj, items: List[Dict[str, Any]], dry_run: bool = False):
    from wareApp.models import BlockInfo

    for it in items:
        defaults = {"is_active": it.get("is_active", True), "site_id": site_obj}
        if dry_run:
            logging.info("DRY RUN: would upsert Block %s -> %s", it.get("block_name"), defaults)
            continue
        obj, created = BlockInfo.objects.update_or_create(
            block_name=it.get("block_name"),
            defaults={"site_id": site_obj, "is_active": it.get("is_active", True)},
        )
        logging.info("BlockInfo upserted: %s created=%s", obj.id, created)


def upsert_panels(site_obj, items: List[Dict[str, Any]], dry_run: bool = False):
    from wareApp.models import Panel

    for it in items:
        if dry_run:
            logging.info("DRY RUN: would upsert Panel %s", it.get("panel"))
            continue
        obj, created = Panel.objects.update_or_create(panel=it.get("panel"), defaults={"site": site_obj})
        logging.info("Panel upserted: %s created=%s", obj.id, created)


def upsert_floors(site_obj, items: List[Dict[str, Any]], dry_run: bool = False):
    from wareApp.models import Floor

    for it in items:
        if dry_run:
            logging.info("DRY RUN: would upsert Floor %s", it.get("floor"))
            continue
        obj, created = Floor.objects.update_or_create(floor=it.get("floor"), defaults={"site": site_obj})
        logging.info("Floor upserted: %s created=%s", obj.id, created)


def upsert_smart_devices(site_obj, items: List[Dict[str, Any]], dry_run: bool = False):
    from wareApp.models import AisleGroup, SmartEnergyDevices

    for it in items:
        defaults = {
            "associated_site": site_obj,
            "device_type": it.get("device_type"),
            "topic": it.get("topic") or "",
            "leg_id": it.get("leg_id"),
            "ref_reading": it.get("ref_reading", 0),
        }
        aisle = None
        if it.get("aisle_grp_id") is not None:
            aisle = AisleGroup.objects.filter(aisle_grp_id=it.get("aisle_grp_id"), site=site_obj).first()
            if aisle:
                defaults["associated_aisle_group"] = aisle

        if dry_run:
            logging.info(
                "DRY RUN: would upsert SmartEnergyDevice %s -> %s",
                it.get("topic"),
                defaults,
            )
            continue

        obj, created = SmartEnergyDevices.objects.update_or_create(topic=it.get("topic") or "", defaults=defaults)
        logging.info("SmartEnergyDevice upserted: %s created=%s", obj.id, created)


def provision_from_payload(payload: Dict[str, Any], dry_run: bool = False):
    site_obj = None
    if "site" in payload and payload["site"]:
        site_obj = upsert_site(payload["site"], dry_run=dry_run)

    if site_obj is None and "site_id" in payload:
        # try to resolve site by id
        from wareApp.models import Site

        site_obj = Site.objects.filter(pk=payload.get("site_id")).first()

    if not site_obj:
        logging.warning("No site context available; aborting provisioning")
        return

    if "home_gateways" in payload:
        upsert_home_gateways(site_obj, payload.get("home_gateways", []), dry_run=dry_run)
    if "aisle_groups" in payload:
        upsert_aisle_groups(site_obj, payload.get("aisle_groups", []), dry_run=dry_run)
    if "blocks" in payload:
        upsert_blocks(site_obj, payload.get("blocks", []), dry_run=dry_run)
    if "panels" in payload:
        upsert_panels(site_obj, payload.get("panels", []), dry_run=dry_run)
    if "floors" in payload:
        upsert_floors(site_obj, payload.get("floors", []), dry_run=dry_run)
    if "smart_devices" in payload:
        upsert_smart_devices(site_obj, payload.get("smart_devices", []), dry_run=dry_run)


def fetch_payload(url: str, auth: Optional[tuple] = None, headers: Optional[dict] = None) -> Optional[Dict[str, Any]]:
    try:
        resp = requests.get(url, timeout=20, auth=auth, headers=headers)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logging.exception("Failed to fetch payload from %s: %s", url, e)
        return None


def main(argv: Optional[List[str]] = None):
    parser = argparse.ArgumentParser()
    # try to import defaults from ProvisioningScriptSavingMeterwisefina if present
    try:
        from ProvisioningScriptSavingMeterwisefina import BASE_URL as DEFAULT_BASE_URL
        from ProvisioningScriptSavingMeterwisefina import HEADERS as DEFAULT_HEADERS
    except Exception:
        DEFAULT_BASE_URL = None
        DEFAULT_HEADERS = None

    parser.add_argument(
        "--url",
        required=DEFAULT_BASE_URL is None,
        default=DEFAULT_BASE_URL,
        help="Endpoint to fetch site provisioning JSON",
    )
    parser.add_argument("--site-id", type=int, help="Optional site id to fetch specific site")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch all sites from the endpoint (if supported)",
    )
    parser.add_argument("--username", help="HTTP basic auth username")
    parser.add_argument("--password", help="HTTP basic auth password")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to DB; only print actions")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    setup_django()

    auth = (args.username, args.password) if args.username and args.password else None
    # prefer headers from ProvisioningScriptSavingMeterwisefina if available
    headers = DEFAULT_HEADERS if DEFAULT_HEADERS is not None else None
    # allow overriding URL if --url provided explicitly
    url = args.url or DEFAULT_BASE_URL

    payload = fetch_payload(url, auth=auth, headers=headers)
    if payload is None:
        logging.error("No payload fetched; exiting")
        sys.exit(1)

    # support endpoints returning list of sites
    if isinstance(payload, list):
        for p in payload:
            provision_from_payload(p, dry_run=args.dry_run)
    else:
        provision_from_payload(payload, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
