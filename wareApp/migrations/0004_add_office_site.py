"""
Module wareApp.migrations.0004_add_office_site

Flow:
Top-level functions:
- create_office_site
- reverse_func
Top-level classes:
- Migration
"""

from django.db import migrations


def create_office_site(apps, schema_editor):
    Site = apps.get_model("wareApp", "Site")
    HomeGatewayId = apps.get_model("wareApp", "HomeGatewayId")

    # create or get site with pk=164
    site_defaults = {"site_name": "office", "location": "office"}
    site, created = Site.objects.get_or_create(pk=164, defaults=site_defaults)

    # create or update HomeGatewayId
    hgw_defaults = {
        "connected_to_id": site.id,
        "rssh_port": "40293",
        "monitoring_port": "40292",
    }
    HomeGatewayId.objects.update_or_create(hgw_id="avc_office_office_000164_1", defaults=hgw_defaults)


def reverse_func(apps, schema_editor):
    Site = apps.get_model("wareApp", "Site")
    HomeGatewayId = apps.get_model("wareApp", "HomeGatewayId")
    try:
        HomeGatewayId.objects.filter(hgw_id="avc_office_office_000164_1").delete()
        Site.objects.filter(pk=164).delete()
    except Exception:
        pass


class Migration(migrations.Migration):
    dependencies = [("wareApp", "0005_remove_aislegroup_wa_aisle_site_grp_idx_and_more")]

    operations = [migrations.RunPython(create_office_site, reverse_func)]
