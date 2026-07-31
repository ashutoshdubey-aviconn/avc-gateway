"""
flake8: noqa

Flow:
Top-level functions:
- entryExit: Trace entry, exit and exceptions.
- create_customer
- create_newCustomer
- create_site
- fetch_site_id
- create_aisle_group
- fetch_all_aisle_groups
- create_home_gateway_id
- fetch_home_gateway
- create_smart_energy_devices
Top-level classes:
- UserViewSet: API endpoint that allows users to be viewed or edited.
- GroupViewSet: API endpoint that allows groups to be viewed or edited.
"""

# flake8: noqa
import logging
from datetime import time

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group, User
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from .models import (
    AisleGroup,
    CustomerInfo,
    HomeGatewayId,
    MeterSource,
    Site,
    SmartEnergyDevices,
)
from .models import User as LocalUser

# from warehouse.wareApp import sendmail
from .serializers import LoginSerializer, TokenSerializer, UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """

    User = get_user_model()
    queryset = User.objects.all().order_by("-date_joined")
    # serializer_class = UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """

    queryset = Group.objects.all()
    # serializer_class = GroupSerializer


def entryExit(aFunc):
    """Trace entry, exit and exceptions."""

    def loggedFunc(*args, **kw):
        logger.debug("*********************")
        logger.info(
            "enter In Function : %s at %s",
            aFunc.__name__,
            str(time.strftime("%I:%M:%S %p")),
        )
        try:
            result = aFunc(*args, **kw)
            logger.info("These are the arguments %s and results %s", args, result)
        except Exception as e:
            logger.exception("exception in %s and %s", aFunc.__name__, e)

        logger.info(
            "exit from Function : %s at %s",
            aFunc.__name__,
            str(time.strftime("%I:%M:%S %p")),
        )
        logger.debug("*********************")
        return result

    loggedFunc.__name__ = aFunc.__name__
    loggedFunc.__doc__ = aFunc.__doc__
    return loggedFunc


def create_customer(data):
    user = User.objects.create(
        username=data["customer_name"],
        email=data["customer_email"],
        password=make_password("Aviconn@123#"),
        UserType=4,
        Contact_number=data["customer_contact"],
        id=data["id"],
    )
    customer = CustomerInfo.objects.create(customer=user)
    return user.id


def create_newCustomer(APIView):
    def post(self, request):
        data = request.data
        customer_id = data.get("customer_id")
        username = data.get("customer_name")
        password = "Aviconn@123#"
        customer_type = 4
        email = data.get("customer_email")
        contact = data.get("customer_contact")
        currentdate = timezone.now()
        user = User.objects.create(
            id=customer_id,
            username=username,
            password=make_password(password),
            email=email,
            Contact_number=contact,
            UserType=customer_type,
        )
        if user:
            customer = CustomerInfo.objects.create(customer=user)
            return Response({"status": 200, "msg": "user created", "user_id": user.id})


def create_site(data):
    customer = User.objects.get(id=data["customer_id"])
    site = Site.objects.create(
        customer=customer,
        site_name=data["site_name"],
        site_type=data["site_type"],
        location=data["site_location"],
        id=data["site_id"],
    )
    return site.id


def fetch_site_id():
    return Site.objects.all()[0].id


def create_aisle_group(data):
    site = Site.objects.get(id=data["site_id"])
    if site.site_type == 1:
        aisle_group = AisleGroup.objects.create(
            site=site,
            aisleGroupName=data["aisle_name"],
            aisle_grp_id=data["aisle_id"],
            power_source=data["power_source"],
            is_this_power_source=True,
            id=data["aisle_id"],
        )
    else:
        aisle_group = AisleGroup.objects.create(
            site=site,
            aisleGroupName=data["aisle_name"],
            aisle_grp_id=data["aisle_id"],
            id=data["aisle_id"],
        )
    return aisle_group.aisle_grp_id


def fetch_all_aisle_groups():
    return AisleGroup.objects.all()


def create_home_gateway_id(data):
    site = Site.objects.get(id=data["site_id"])
    home_gateway = HomeGatewayId.objects.create(
        hgw_id=data["home_gateway_name"],
        connected_to=site,
        rssh_port=data["rssh_port"],
        monitoring_port=data["monitoring_port"],
    )
    return home_gateway.id


def fetch_home_gateway():
    return HomeGatewayId.objects.all()[0]


"""def create_meter_source(data):
    site = Site.objects.all()[0]
    meter_source = MeterSource.objects.create(Associated_Site=site, meter_id=data["meter_id"], meter_number=data["meter_number"],
                                              meter_type=data["meter_type"])
    if 'power_source_1' in data:
        meter_source.update(power_source_1=data["power_source_1"])
    if 'power_source_2' in data:
        meter_source.update(power_source_2=data["power_source_2"])
    if 'power_source_1' in data and 'power_source_2' in data:
        meter_source.update(power_source_1=data['power_source_1'], power_source_2=data['power_source_2'],
                            is_PS2_valid=True)
    return meter_source.id"""


def create_smart_energy_devices(data):
    aisle_group = AisleGroup.objects.get(id=data["leg_id"])
    site = Site.objects.all()[0]
    device = SmartEnergyDevices.objects.create(
        associated_site=site,
        associated_aisle_group=aisle_group,
        device_type=1,
        topic=data["topic"],
        leg_id=data["leg_id"],
    )
    return device.id


def fetch_smart_energy_devices():
    devices = SmartEnergyDevices.objects.all()
    return devices


def create_meter_source(data):
    site_id = Site.objects.all()[0]
    if "power_source_2" in data:
        MeterSource.objects.create(
            Associated_Site=site_id,
            meter_id=data["meter_id"],
            meter_number=data["meter_id"],
            meter_type=data["meter_type"],
            power_source_1=data["power_source_1"],
            power_source_2=data["power_source_2"],
            is_PS2_valid=True,
        )
    else:
        MeterSource.objects.create(
            Associated_Site=site_id,
            meter_id=data["meter_id"],
            meter_number=data["meter_id"],
            meter_type=data["meter_type"],
            power_source_1=data["power_source_1"],
        )
    return True


def fetch_meter_source_records(meter_id):
    return MeterSource.objects.filter(meter_number=meter_id)


def fetch_all_meters():
    return MeterSource.objects.all()


def fetch_site_type_from_gateway():
    return Site.objects.all()[0].site_type


def dummy():
    return {"status": "ok"}
