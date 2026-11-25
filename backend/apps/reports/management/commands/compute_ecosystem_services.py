"""Recompute the carbon stock and intercepted rain of every active tree.

Run it after loading or correcting census data (the estimates fill missing inputs with
medians of the whole census, so every tree is recomputed):

    python manage.py compute_ecosystem_services
"""

from django.core.management.base import BaseCommand

from apps.reports.ecosystem import CO2_PER_C, refresh


class Command(BaseCommand):
    help = "Recompute the ecosystem services (carbon stock, intercepted rain) of every tree."

    def handle(self, *args, **options):
        rows = refresh()
        carbon_t = sum(r["carbon_kg"] or 0 for r in rows) / 1000
        rain = sum(r["rain_interception_m3"] or 0 for r in rows)
        imputed = sum(1 for r in rows if r["imputed"])
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(rows):,} trees: {carbon_t:,.0f} t C stored "
                f"({carbon_t * CO2_PER_C:,.0f} t CO2e), {rain:,.0f} m3/year of rain "
                f"intercepted; {imputed:,} with some imputed input."
            )
        )
