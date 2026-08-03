#!/usr/bin/env python3
"""Live sync script: fetch data from a remote server and upsert into local DB.

Usage examples:
  ./venv/bin/python scripts/live_sync.py --url https://example.com/sync --once
  ./venv/bin/python scripts/live_sync.py --url https://example.com/sync --interval 30

Expected JSON structure (flexible):
  {
    "daily": [ {"site_id": 1, "leg_id": "A1", "reading_for": "2026-07-30", "unit_consumption": 12.3}, ... ],
    "hourly": [ {"site_id": 1, "leg_id": "A1", "reading_from": "2026-07-30T10:00:00", "reading_to": "2026-07-30T11:00:00", "unit_consumption": 1.2}, ... ],
    "supply": [ {"site_id": 1, "power_source": 0, "reading_from": "2026-07-30T10:00:00", "reading_to": "2026-07-30T11:00:00", "hourly_run_time": 45}, ... ]
  }

The script is intentionally conservative: it only updates or creates records when it can match required fields.
"""

import argparse
import json
import logging
import os
import time
from datetime import date, datetime
from typing import Any, Dict, Optional

import requests


def setup_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "warehouse.settings")
    import django

    django.setup()


def parse_date(s: Any) -> Optional[date]:
    if s is None:
        return None
    if isinstance(s, date) and not isinstance(s, datetime):
        return s
    try:
        return date.fromisoformat(str(s))
    except Exception:
        pass
    try:
        return datetime.fromisoformat(str(s)).date()
    except Exception:
        pass
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(s), fmt).date()
        except Exception:
            pass
    return None


def parse_datetime(s: Any) -> Optional[datetime]:
    if s is None:
        return None
    if isinstance(s, datetime):
        return s
    try:
        return datetime.fromisoformat(str(s))
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(str(s), fmt)
        except Exception:
            pass
    return None


def upsert_daily(entries: list[Dict[str, Any]]):
    from wareApp.models import AisleGroup, DailySiteReading, Site

    for e in entries:
        site_id = e.get("site_id")
        leg_id = e.get("leg_id") or e.get("aisle_group") or e.get("aisle")
        reading_for = parse_date(e.get("reading_for") or e.get("date"))
        unit = e.get("unit_consumption") or e.get("unit") or e.get("consumption")

        site = Site.objects.filter(id=site_id).first() if site_id else None
        aisle = None
        if leg_id is not None:
            aisle = AisleGroup.objects.filter(aisle_grp_id=leg_id).first()

        if reading_for is None:
            logging.warning("Skipping daily entry without parsable date: %s", e)
            continue

        obj, created = DailySiteReading.objects.update_or_create(
            associated_Site=site,
            aisle_group=aisle,
            leg_id=leg_id,
            reading_for=reading_for,
            defaults={"unit_consumption": unit},
        )
        logging.info("Upserted daily reading: %s created=%s", obj.pk, created)


def upsert_hourly(entries: list[Dict[str, Any]]):
    from wareApp.models import AisleGroup, HourlySiteReading, Site

    for e in entries:
        site_id = e.get("site_id")
        leg_id = e.get("leg_id") or e.get("aisle_group") or e.get("aisle")
        rf = parse_datetime(e.get("reading_from"))
        rt = parse_datetime(e.get("reading_to"))
        unit = e.get("unit_consumption") or e.get("unit") or e.get("consumption")

        site = Site.objects.filter(id=site_id).first() if site_id else None
        aisle = None
        if leg_id is not None:
            aisle = AisleGroup.objects.filter(aisle_grp_id=leg_id).first()

        if rf is None or rt is None:
            logging.warning("Skipping hourly entry without from/to datetimes: %s", e)
            continue

        obj, created = HourlySiteReading.objects.update_or_create(
            associated_Site=site,
            aisle_group=aisle,
            leg_id=leg_id,
            reading_from=rf,
            reading_to=rt,
            defaults={"unit_consumption": unit},
        )
        logging.info("Upserted hourly reading: %s created=%s", obj.pk, created)


def upsert_supply(entries: list[Dict[str, Any]]):
    from wareApp.models import Site, SupplyLoadTimeShare

    for e in entries:
        site_id = e.get("site_id")
        power_source = e.get("power_source")
        rf = parse_datetime(e.get("reading_from")) or parse_datetime(e.get("last_synced"))
        rt = parse_datetime(e.get("reading_to")) or parse_datetime(e.get("end"))
        runtime = e.get("hourly_run_time") or e.get("runtime")

        site = Site.objects.filter(id=site_id).first() if site_id else None
        if site is None:
            logging.warning("Skipping supply entry without valid site: %s", e)
            continue
        if rf is None or rt is None:
            logging.warning("Skipping supply entry without timestamps: %s", e)
            continue

        obj, created = SupplyLoadTimeShare.objects.update_or_create(
            site=site,
            power_source=power_source,
            reading_from=rf,
            reading_to=rt,
            defaults={"hourly_run_time": runtime},
        )
        logging.info("Upserted supply runtime: %s created=%s", obj.pk, created)


def process_payload(payload: Dict[str, Any]):
    if not isinstance(payload, dict):
        logging.warning("Unexpected payload format; expecting JSON object")
        return

    if "daily" in payload:
        upsert_daily(payload.get("daily", []))
    if "hourly" in payload:
        upsert_hourly(payload.get("hourly", []))
    if "supply" in payload:
        upsert_supply(payload.get("supply", []))


def fetch_and_process(url: str, auth: Optional[tuple] = None, headers: Optional[dict] = None):
    try:
        resp = requests.get(url, timeout=15, auth=auth, headers=headers)
        resp.raise_for_status()
    except Exception as exc:
        logging.exception("Failed to fetch %s: %s", url, exc)
        return

    try:
        payload = resp.json()
    except Exception as exc:
        logging.exception("Failed to decode JSON from %s: %s", url, exc)
        return

    process_payload(payload)


def main():
    parser = argparse.ArgumentParser()
    # try to reuse BASE_URL and HEADERS from ProvisioningScriptSavingMeterwisefina
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
        help="Endpoint URL to fetch JSON sync data from",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help="Polling interval in seconds (0 = run once)",
    )
    parser.add_argument("--username", help="HTTP basic auth username")
    parser.add_argument("--password", help="HTTP basic auth password")
    parser.add_argument(
        "--header",
        action="append",
        help="Extra header NAME:VALUE (can be passed multiple times)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    setup_django()

    auth = (args.username, args.password) if args.username and args.password else None
    headers = DEFAULT_HEADERS.copy() if DEFAULT_HEADERS is not None else {}
    if args.header:
        for h in args.header:
            if ":" in h:
                k, v = h.split(":", 1)
                headers[k.strip()] = v.strip()

    url = args.url
    if args.interval <= 0:
        fetch_and_process(url, auth=auth, headers=headers)
        return

    logging.info("Starting live sync loop: fetching %s every %s seconds", args.url, args.interval)
    while True:
        fetch_and_process(args.url, auth=auth, headers=headers)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
