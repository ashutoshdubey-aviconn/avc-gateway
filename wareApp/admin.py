# flake8: noqa
from django.contrib import admin

from .models import (
    AisleGroup,
    AisleInfo,
    AlarmNotifications,
    BlockInfo,
    CustomerInfo,
    DailySiteReading,
    Floor,
    HomeGatewayId,
    HourlySiteReading,
    Image,
    LoadData,
    MeterReadings,
    MeterSource,
    Panel,
    Site,
    SiteLoadPower,
    SmartEnergyDevices,
    SupplyLoadTimeShare,
    User,
)


class HourlyReadingFields(admin.ModelAdmin):
    list_display = [
        "associated_Site",
        "aisle_group",
        "unit_consumption",
        "reading_from",
        "reading_to",
    ]

    class Meta:
        model = HourlySiteReading


class SupplyTimeShareFields(admin.ModelAdmin):
    list_display = [
        "site",
        "power_source",
        "hourly_run_time",
        "reading_from",
        "reading_to",
    ]

    class Meta:
        model = SupplyLoadTimeShare


class siteLoadPower(admin.ModelAdmin):
    list_display = ["Associated_Site", "Supply_Source", "Status"]
    readonly_fields = ("Supply_Source", "Meter_Number")

    class Meta:
        model = SiteLoadPower


admin.site.register(User)
admin.site.register(CustomerInfo)
admin.site.register(Site)
admin.site.register(Image)
admin.site.register(BlockInfo)
admin.site.register(AisleInfo)
admin.site.register(HourlySiteReading, HourlyReadingFields)
admin.site.register(AlarmNotifications)
admin.site.register(SupplyLoadTimeShare, SupplyTimeShareFields)
admin.site.register(SiteLoadPower, siteLoadPower)
admin.site.register(AisleGroup)
admin.site.register(Panel)
admin.site.register(Floor)
admin.site.register(MeterSource)
admin.site.register(DailySiteReading)
admin.site.register(HomeGatewayId)
admin.site.register(SmartEnergyDevices)
admin.site.register(MeterReadings)
admin.site.register(LoadData)
