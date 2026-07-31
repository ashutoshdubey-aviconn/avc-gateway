import json

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Print counts and sample AisleGroup cumulative_consumption; output JSON optionally to file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            dest="out",
            help="Path to write JSON output (default: stdout)",
            default=None,
        )
        parser.add_argument(
            "--limit",
            dest="limit",
            type=int,
            help="Number of AisleGroup samples to include",
            default=10,
        )

    def handle(self, *args, **options):
        from wareApp.models import AisleGroup, DailySiteReading, HourlySiteReading

        hourly_count = HourlySiteReading.objects.count()
        daily_count = DailySiteReading.objects.count()

        # Use values() to avoid loading model instances
        aisle_qs = AisleGroup.objects.values("id", "cumulative_consumption").order_by("id")[: options["limit"]]

        result = {
            "hourly_count": hourly_count,
            "daily_count": daily_count,
            "aisle_sample": list(aisle_qs),
        }

        out_path = options.get("out")
        if out_path:
            with open(out_path, "w") as f:
                json.dump(result, f, indent=2, default=str)
            self.stdout.write(self.style.SUCCESS(f"Wrote JSON to {out_path}"))
        else:
            self.stdout.write(json.dumps(result, indent=2, default=str))


import json

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Dump counts and sample AisleGroup values for quick DB checks"

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            "-o",
            help="Output file path (writes JSON). If omitted, prints to stdout",
            default=None,
        )
        parser.add_argument(
            "--limit",
            "-n",
            type=int,
            default=10,
            help="Number of AisleGroup rows to include (default: 10)",
        )

    def handle(self, *args, **options):
        outpath = options.get("out")
        limit = options.get("limit") or 10

        # Import models inside handle to avoid import-time side effects
        try:
            from wareApp.models import AisleGroup, DailySiteReading, HourlySiteReading
        except Exception as e:
            self.stderr.write(f"Error importing models: {e}")
            raise

        try:
            # Use database COUNT() for efficient counts
            hourly_count = HourlySiteReading.objects.count()
            daily_count = DailySiteReading.objects.count()

            # Use values() to fetch only needed fields and limit rows
            aisles_qs = AisleGroup.objects.values("id", "cumulative_consumption").order_by("id")[:limit]
            aisles = list(aisles_qs)

            result = {
                "hourly_count": hourly_count,
                "daily_count": daily_count,
                "aisles_sample": aisles,
            }

            out_text = json.dumps(result, indent=2, default=str)

            if outpath:
                with open(outpath, "w") as f:
                    f.write(out_text)
                self.stdout.write(self.style.SUCCESS(f"Wrote DB check JSON to {outpath}"))
            else:
                self.stdout.write(out_text)

        except Exception as exc:
            self.stderr.write(f"Error while querying database: {exc}")
            raise
