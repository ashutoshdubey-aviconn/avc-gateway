import logging

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.utils import timezone
from django_extensions.db.models import TimeStampedModel
from mptt.models import MPTTModel, TreeForeignKey

logger = logging.getLogger(__name__)


class User(AbstractUser):
    user_type = (
        (1, "Super_Admin"),
        (2, "Aviconn_Admin"),
        (3, "Aviconn_Executive"),
        (4, "Customer"),
        (5, "Cust_Site_Manager"),
    )
    UserType = models.PositiveIntegerField(default=1, choices=user_type)
    Contact_number = models.CharField(max_length=10, help_text="Enter the 10 digit mobile number")


def Create_Group(sender, instance, *args, **kwargs):
    if instance._state.adding is True and len(Group.objects.filter(name=instance.get_UserType_display())):
        logger.info("Group has been created successfully: %s", instance.get_UserType_display())
        Group.objects.create(name=instance.get_UserType_display())


def Add_group_to_user(sender, instance, *args, **kwargs):
    try:
        if instance.UserType == 1:
            User.objects.filter(username=instance.username).update(is_staff=True)
        g = Group.objects.filter(name=instance.get_UserType_display())
        logger.debug("Groups matched for user %s: %s", instance.username, list(g))
        logger.info("Instance has been added inside the group")
        instance.groups.set(g)

    except Exception as e:
        logger.exception("Error adding user to group: %s", e)


post_save.connect(Add_group_to_user, sender=User)
pre_save.connect(Create_Group, sender=User)


class CustomerInfo(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="customer",
        on_delete=models.CASCADE,
        blank=False,
    )
    address = models.CharField(max_length=30, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    total_energy_consumed = models.FloatField(default=0.0)
    total_energy_saved = models.FloatField(default=0.0)
    total_sites = models.PositiveIntegerField(default=0.0)

    def __unicode__(self):
        return self.customer.username

    def __str__(self):
        return self.customer.username


class Site(models.Model):
    customer = models.ForeignKey(User, related_name="site", on_delete=models.CASCADE, null=True, blank=True)
    site_name = models.CharField(max_length=20)
    SITE_TYPE = ((1, "WH_Metering"), (2, "WH_Energy_Saving"), (3, "WH_AssetTracking"))
    site_type = models.PositiveIntegerField(choices=SITE_TYPE, null=True, blank=True)
    total_no_of_blocks = models.PositiveIntegerField(null=True, blank=True)
    total_no_of_aisles = models.PositiveIntegerField(null=True, blank=True)
    location = models.CharField(max_length=20, null=True, blank=True)
    per_unit_cost = models.FloatField(null=True, blank=True)
    genset_unit_rate = models.FloatField(null=True, blank=True)
    no_of_single_source_meters = models.PositiveIntegerField(null=True, blank=True)
    no_of_dual_source_meters = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=False)
    live_date = models.DateTimeField(null=True, blank=True)
    current_baseline = models.FloatField(null=True, blank=True)
    consumed_energy = models.FloatField(null=True, blank=True)
    total_energy_saved = models.FloatField(null=True, blank=True)
    site_manager = models.ForeignKey(
        User,
        related_name="site_manager",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    avg_saving = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.site_name

    def __unicode__(self):
        return self.site_name


class HomeGatewayId(models.Model):
    hgw_id = models.CharField(max_length=200)
    owned_by = models.ForeignKey(
        CustomerInfo,
        related_name="owned_by",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    connected_to = models.ForeignKey(
        Site,
        related_name="connected_to",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    rssh_port = models.CharField(max_length=10, unique=True, blank=True, null=True)
    monitoring_port = models.CharField(max_length=10, unique=True, blank=True, null=True)

    def __unicode__(self):
        return self.hgw_id

    def __str__(self):
        return self.hgw_id


class Image(models.Model):
    which_site = models.ForeignKey(Site, on_delete=models.CASCADE, null=True, blank=True)
    image_file = models.FileField()
    image_id = models.CharField(max_length=10)

    def __str__(self):
        return self.image_file

    def __unicode__(self):
        return self.image_file


class BlockInfo(models.Model):
    block_name = models.CharField(max_length=10)
    site_id = models.ForeignKey(Site, on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField()

    def __str__(self):
        return self.block_name

    def __unicode__(self):
        return self.block_name


class Panel(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, null=True, blank=True)
    panel = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.panel

    def __unicode__(self):
        return self.panel


class Floor(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, null=True, blank=True)
    FLOOR = (
        ("GF", "Ground Floor"),
        ("F1", "First Floor"),
        ("F2", "Second Floor"),
        ("F3", "Third Floor"),
        ("F4", "Fourth Floor"),
        ("F5", "Fifth Floor"),
    )
    floor = models.CharField(max_length=30, choices=FLOOR, null=True, blank=True)

    def __str__(self):
        return self.floor

    def __unicode__(self):
        return self.floor


class MonthlyEnergySaving(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, null=True, blank=True)
    monthly_saving = models.FloatField(null=True, blank=True)
    percentage_monthly_saving = models.FloatField(null=True, blank=True)
    total_saving_till_date = models.FloatField(null=True, blank=True)
    created = models.DateField()

    def __str__(self):
        return self.percentage_monthly_saving

    def __unicode__(self):
        return self.percentage_monthly_saving


class AisleGroup(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, null=True, blank=True)
    aisle_grp_id = models.PositiveIntegerField(null=True, blank=True)
    block_id = models.ManyToManyField(BlockInfo, blank=True)
    panel = models.ManyToManyField(Panel, blank=True)
    floor = models.ManyToManyField(Floor, blank=True)
    aisleGroupName = models.CharField(max_length=100)
    total_lights = models.IntegerField(blank=True, null=True)
    one_light_watt = models.IntegerField(blank=True, null=True)
    expected_consumption = models.FloatField(blank=True, null=True)
    is_active = models.BooleanField(default=False)
    cumulative_consumption = models.FloatField(default=0)
    # is_visible = models.BooleanField(default=False)
    # visible_date = models.DateField(blank=True, null=True)
    is_this_power_source = models.BooleanField(default=False)
    sources = (
        (0, "MAINS SUPPLY"),
        (1, "DG 1"),
        (2, "DG 2"),
        (3, "DG 3"),
        (4, "DG 4"),
        (5, "DG 5"),
    )
    power_source = models.PositiveIntegerField(default=0, choices=sources)

    def __str__(self):
        return self.aisleGroupName + " " + str(self.site)

    def __unicode__(self):
        return self.aisleGroupName + " " + str(self.site)


class AisleInfo(models.Model):
    aisle_name = models.CharField(max_length=100)
    aisle_group = models.ForeignKey(AisleGroup, on_delete=models.CASCADE, null=True, blank=True)
    total_lights = models.IntegerField(blank=True, null=True)
    one_light_watt = models.IntegerField(blank=True, null=True)
    total_number_of_sensors = models.PositiveIntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.aisle_name

    def __unicode__(self):
        return self.aisle_name


class HourlySiteReading(models.Model):
    associated_Site = models.ForeignKey(Site, on_delete=models.CASCADE, null=True, blank=True)
    aisle_group = models.ForeignKey(AisleGroup, on_delete=models.CASCADE, null=True, blank=True)
    leg_id = models.CharField(max_length=50, null=True, blank=True)
    unit_consumption = models.FloatField(null=True, blank=True)
    reading_from = models.DateTimeField(blank=True, null=True)
    reading_to = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return str(self.leg_id)


class DailySiteReading(models.Model):
    associated_Site = models.ForeignKey(Site, on_delete=models.CASCADE, null=True, blank=True)
    aisle_group = models.ForeignKey(AisleGroup, on_delete=models.CASCADE, null=True, blank=True)
    leg_id = models.CharField(max_length=50, null=True, blank=True)
    unit_consumption = models.FloatField(null=True, blank=True)
    reading_for = models.DateField(default=timezone.now)

    def __str__(self):
        return str(self.leg_id)


class AlarmNotifications(models.Model):
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    site_id = models.ForeignKey(Site, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    alarm_type = (
        (0, "Low_balance"),
        (1, "Power_Cut"),
        (2, "Pending Balance"),
        (3, "Pending Request"),
        (4, "Zero balance"),
        (5, "Box opened"),
        (6, "Internet_Gone"),
        (7, "No meter reading"),
    )
    Alarm_type = models.PositiveIntegerField(choices=alarm_type)
    create_DateTime = models.DateTimeField(auto_now=False, auto_now_add=True)
    alarm_priorities = ((0, "Normal"), (1, "High"))
    Alarm_priority = models.PositiveIntegerField(choices=alarm_priorities, default=0)
    actual_created = models.DateTimeField(default=timezone.now)
    to_do = models.CharField(max_length=200, blank=True, null=True)
    off_time = models.DateTimeField(default=timezone.now)
    cloud_time = models.DateTimeField(auto_now=False, auto_now_add=True)
    is_active = models.BooleanField(default=True)

    # def __unicode__(self):
    # return "Notification for {}".format(str(self.site_id))

    # def __str__(self):
    # return "Notification for {}".format(str(self.site_id))


class SensorData(models.Model):
    sensor_id = models.CharField(max_length=10)
    sensor_associated_with = models.ForeignKey(AisleGroup, on_delete=models.CASCADE)
    sensor_status = models.BooleanField()
    sensor_on_date_time = models.DateTimeField()
    sensor_off_date_time = models.DateTimeField()


class SiteStaticData(models.Model):
    site_id = models.ForeignKey(Site, on_delete=models.CASCADE)
    block_id = models.ForeignKey(BlockInfo, on_delete=models.CASCADE)
    aisle_group = models.ForeignKey(AisleGroup, on_delete=models.CASCADE)
    aisle_id = models.ForeignKey(AisleInfo, on_delete=models.CASCADE)
    sensor_id = models.ForeignKey(SensorData, on_delete=models.CASCADE)
    total_lights = models.PositiveIntegerField()
    total_watts = models.CharField(max_length=100)


class OTP(models.Model):
    otp = models.CharField(blank=True, null=True, max_length=5)
    user_id = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now=False, auto_now_add=True)

    def __unicode__(self):
        return f"OTP  {self.otp} on {self.created}"

    def __str__(self):
        return f"OTP  {self.otp} on {self.created}"


class SiteLoadPower(models.Model):
    Associated_Site = models.ForeignKey(Site, on_delete=models.CASCADE, null=True, blank=True)
    Site_Total_Load = models.FloatField(blank=True, null=True)
    r_volt = models.FloatField(blank=True, null=True)
    y_volt = models.FloatField(blank=True, null=True)
    b_volt = models.FloatField(blank=True, null=True)
    r_current = models.FloatField(blank=True, null=True)
    y_current = models.FloatField(blank=True, null=True)
    b_current = models.FloatField(blank=True, null=True)
    r_power_factor = models.FloatField(blank=True, null=True)
    y_power_factor = models.FloatField(blank=True, null=True)
    b_power_factor = models.FloatField(blank=True, null=True)
    Supply_Source = models.CharField(max_length=20, null=True, blank=True)
    # The above code is not doing anything as it is just a comment in Python. Comments in Python start
    # with a hash symbol (#) and are used to provide explanations or notes within the code for better
    # understanding.
    # The above code is not doing anything as it is just a comment in Python. Comments in Python start
    # with the `#` symbol and are used to provide explanations or notes in the code for better
    # understanding.
    Meter_Number = models.PositiveIntegerField(null=True, blank=True)
    Status = models.CharField(max_length=10, null=True, blank=True)
    Updated_on = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return (
            f"Total Load: {str(self.Site_Total_Load)},R-phase voltage: {str(self.r_volt)}, Y-phase voltage: {str(self.y_volt)}, B-phase voltage: {str(self.b_volt)},"
            f" R-phase current: {str(self.r_current)},"
            f" Y-phase current: {str(self.y_current)}, B-phase current: {str(self.b_current)}, Supply Source: {str(self.Supply_Source)}"
        )

    def __unicode__(self):
        return (
            f"Total Load: {str(self.Site_Total_Load)},R-phase voltage: {str(self.r_volt)}, Y-phase voltage: {str(self.y_volt)}, B-phase voltage: {str(self.b_volt)},"
            f" R-phase current: {str(self.r_current)},"
            f" Y-phase current: {str(self.y_current)}, B-phase current: {str(self.b_current)}"
        )


class MeterSource(models.Model):
    Associated_Site = models.ForeignKey(Site, on_delete=models.CASCADE, null=True, blank=True)
    meter_id = models.PositiveIntegerField(primary_key=True)
    meter_number = models.PositiveIntegerField(null=True, blank=True)
    POWER_SOURCES = (
        (0, "Mains Supply"),
        (1, "DG_1"),
        (2, "DG_2"),
        (3, "DG_3"),
        (4, "DG_4"),
        (5, "DG 5"),
    )
    power_source_1 = models.PositiveIntegerField(choices=POWER_SOURCES, null=True, blank=True)
    power_source_2 = models.PositiveIntegerField(choices=POWER_SOURCES, null=True, blank=True)
    METER_TYPE = ((1, "Single Source"), (2, "Dual Source"))
    meter_type = models.PositiveIntegerField(choices=METER_TYPE, null=True, blank=True)
    is_PS2_valid = models.BooleanField(default=False)

    def __str__(self):
        return str(self.power_source_1) + " " + str(self.power_source_2)

    def __unicode__(self):
        return str(self.power_source_1) + " " + str(self.power_source_2)


class SmartEnergyDevices(MPTTModel, TimeStampedModel):
    associated_site = models.ForeignKey(Site, on_delete=models.CASCADE, null=True, blank=True)
    DEVICE_TYPE = ((1, "METER"), (2, "SENSOR"))
    device_type = models.PositiveIntegerField(choices=DEVICE_TYPE, null=True, blank=True)  # device type enum
    topic = models.CharField(max_length=100, default="")
    leg_id = models.PositiveIntegerField(null=True, blank=True)
    associated_aisle_group = models.ForeignKey(AisleGroup, on_delete=models.CASCADE, null=True, blank=True)
    ref_reading = models.FloatField(default=0)
    parent = TreeForeignKey("self", null=True, blank=True, related_name="children", on_delete=models.CASCADE)
    is_other_gw = models.BooleanField(default=False)
    # notification = GenericRelation(AlarmNotifications)

    def __unicode__(self):
        return self.topic

    def __str__(self):
        return self.topic


class MeterReadings(models.Model):
    local_meterId = models.PositiveIntegerField(null=True, blank=True)
    reading_type = ((0, "Energy"), (1, "Load_time"), (2, "Sensor"))
    reading_for = models.PositiveIntegerField(choices=reading_type, null=True, blank=True)
    reading_of = models.CharField(max_length=100, null=True, blank=True)
    previous_reading_value = models.CharField(max_length=100, null=True, blank=True)
    # cumulative_units = models.PositiveIntegerField(default=0)
    updated_on = models.DateTimeField(default=timezone.now)

    def __unicode__(self):
        return self.reading_of

    def __str__(self):
        return self.reading_of


class SupplyLoadTimeShare(models.Model):
    site = models.ForeignKey(Site, related_name="supply", on_delete=models.CASCADE)
    sources = (
        (0, "MAINS SUPPLY"),
        (1, "DG 1"),
        (2, "DG 2"),
        (3, "DG 3"),
        (4, "DG 4"),
        (5, "DG 5"),
    )
    power_source = models.PositiveSmallIntegerField(default=0, choices=sources)
    hourly_run_time = models.IntegerField(default=0)
    reading_from = models.DateTimeField(default=timezone.now)
    reading_to = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.get_power_source_display()


class LoadData(models.Model):
    Associated_Site = models.ForeignKey(Site, on_delete=models.CASCADE, null=True, blank=True)
    leg_id = models.PositiveIntegerField(null=True, blank=True)
    site_total_load = models.FloatField(blank=True, null=True)
    Meter_Number = models.PositiveIntegerField(null=True, blank=True)
    Updated_on = models.DateTimeField(blank=True, null=True)
    epochTime = models.CharField(max_length=60, blank=True, null=True)

    def __str__(self):
        return str(self.site_total_load)


"""class SupplyTimeShare(models.Model):

    Associated_Site = models.ForeignKey(Site, on_delete=models.CASCADE, null=True, blank=True)
    Power_Source = models.CharField(max_length=20)
    Last_runtime_cumulative = models.IntegerField(null=False)
    Updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.Power_Source + ": " + str(self.Last_runtime_cumulative)

    def __unicode__(self):
        return self.Power_Source + ": " + str(self.Last_runtime_cumulative)"""
