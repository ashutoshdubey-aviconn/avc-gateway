"""Small benchmark for indexed recovery queries.

Run this script from the repository root:
    python3 scripts/index_benchmark.py

It creates sample rows (if needed) and measures query time for the
hourly-reading range query used by recovery.
"""

import os
import random
import sys
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "warehouse.settings")

import django

# Ensure project root is on path so Django can import the project package
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

django.setup()

from django.utils import timezone

from wareApp.models import AisleGroup, HourlySiteReading, Site


def ensure_sample_data(count: int = 500):
    site = Site.objects.first()
    if site is None:
        site = Site.objects.create(site_name="bench-site")

    aisle = AisleGroup.objects.filter(site=site, aisle_grp_id=1).first()
    if aisle is None:
        aisle = AisleGroup.objects.create(site=site, aisle_grp_id=1, aisleGroupName="bench-aisle")

    existing = HourlySiteReading.objects.filter(leg_id="bench-leg").count()
    to_create = max(0, count - existing)
    now = timezone.now().replace(minute=0, second=0, microsecond=0)
    if to_create > 0:
        objs = []
        for i in range(to_create):
            rf = now + timezone.timedelta(hours=i)
            rt = rf + timezone.timedelta(hours=1)
            objs.append(
                HourlySiteReading(
                    associated_Site=site,
                    aisle_group=aisle,
                    leg_id="bench-leg",
                    unit_consumption=random.random() * 10.0,
                    reading_from=rf,
                    reading_to=rt,
                )
            )
        HourlySiteReading.objects.bulk_create(objs)


def measure(query_time: int = 5):
    now = timezone.now().replace(minute=0, second=0, microsecond=0) + timezone.timedelta(hours=10)
    iterations = 100
    # warmup
    for _ in range(5):
        list(HourlySiteReading.objects.filter(leg_id="bench-leg", reading_from__lte=now, reading_to__gte=now)[:10])

    start = time.perf_counter()
    for _ in range(iterations):
        list(HourlySiteReading.objects.filter(leg_id="bench-leg", reading_from__lte=now, reading_to__gte=now)[:10])
    elapsed = time.perf_counter() - start
    print(f"Ran {iterations} queries in {elapsed:.4f}s: avg {elapsed/iterations*1000:.3f} ms/query")


if __name__ == "__main__":
    print("Ensuring sample data (may take a few seconds)...")
    ensure_sample_data(500)
    print("Measuring query performance...")
    measure()
