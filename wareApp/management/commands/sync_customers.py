"""Management command to sync customer usernames from central cloud.

Usage:
  python manage.py sync_customers [--apply] [--limit N]

By default this runs in dry-run mode and prints a summary of updates it would
perform. Use `--apply` to actually write changes to the local DB.

The command respects the environment variables `PROVISION_BASE_URL` and
`PROVISION_SECRET_TOKEN` to contact the same API used by the provisioning
scripts.
"""

from __future__ import annotations

import json
import os
from typing import Iterable

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sync local usernames from cloud customer records (dry-run by default)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the changes instead of only showing a dry-run",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit number of customers processed (0 = no limit)",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        limit = options["limit"]

        base = os.environ.get("PROVISION_BASE_URL", "https://asem.aviconncorp.com/api/")
        token = os.environ.get("PROVISION_SECRET_TOKEN")
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = token

        import requests
        from django.contrib.auth import get_user_model

        User = get_user_model()

        url = base.rstrip("/") + "/fetchAllCustomers/"
        self.stdout.write(f"Fetching customers from {url} ...")
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            self.stderr.write(f"Failed to fetch customers: {exc}")
            return

        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            # maybe payload is a list itself
            if isinstance(payload, list):
                data = payload
            else:
                self.stderr.write("Unexpected response format from cloud API")
                return

        to_update = []
        processed = 0
        for c in data:
            if limit and processed >= limit:
                break
            processed += 1
            cid = c.get("id")
            if not cid:
                continue
            # prefer cloud username or customer_name, then email
            name = c.get("username") or c.get("customer_name") or c.get("customer_email")
            if not name:
                continue
            try:
                user = User.objects.filter(id=cid).first()
            except Exception:
                # model may use different PK types; skip
                user = None
            if not user:
                continue
            current = getattr(user, "username", None)
            if not current or str(current).startswith("customer_"):
                to_update.append((cid, current, name))

        if not to_update:
            self.stdout.write("No users require updating.")
            return

        self.stdout.write("Planned updates:\n")
        for cid, current, name in to_update:
            self.stdout.write(f"  id={cid} current={current!r} -> new={name!r}")

        self.stdout.write(f"\nTotal candidates: {len(to_update)}")

        if not apply_changes:
            self.stdout.write("\nDry-run mode: no changes applied. Re-run with --apply to commit updates.")
            return

        # Apply changes
        self.stdout.write("\nApplying updates...")
        applied = 0
        for cid, current, name in to_update:
            try:
                user = User.objects.get(id=cid)
                user.username = name
                # do not change passwords; only set username
                user.save()
                applied += 1
            except Exception as exc:
                self.stderr.write(f"Failed updating id={cid}: {exc}")

        self.stdout.write(f"Applied updates: {applied}")
