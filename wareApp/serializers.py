import base64

from django.contrib.auth import authenticate
from django.core import exceptions
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from .models import CustomerInfo, Site, User


class TokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Token
        fields = ["key", "user"]


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        print("dataa")
        username = data.get("username", "")
        password = base64.b64decode(data.get("password", ""))
        print(password)

        if username and password:
            user = authenticate(username=username, password=password)
            print("user", user)
            if user:
                data["user"] = user
            else:
                print("user authentication fails")
                msg = "invalid credentials. try again"
                return exceptions.ValidationError(msg)
        else:
            print("username & password doesnt exist")
            msg = "invalid data"
            return exceptions.ValidationError(msg)

        return data


# for login purpose
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "UserType",
            "first_name",
            "last_name",
            "Contact_number",
        ]


class UserCustomerInfoSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "Contact_number",
            "first_name",
            "last_name",
        ]


class CustomerInfoSerializer(serializers.ModelSerializer):

    customer = UserCustomerInfoSerializer(many=False, read_only=True)

    class Meta:
        model = CustomerInfo
        fields = ["address", "total_sites", "customer"]


class CustomerWarehouseDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = Site
        fields = ["id", "site_name", "site_manager_number"]


class SiteSerializer(serializers.ModelSerializer):

    site_manager = UserSerializer(many=False, read_only=True)

    class Meta:
        model = Site
        fields = [
            "site_name",
            "total_no_of_blocks",
            "total_no_of_aisles",
            "location",
            "no_of_single_source_meters",
            "no_of_dual_source_meters",
            "site_manager",
            "site_type",
            "id",
        ]


# class ParticularCustomerInfoSerializer(serializers.ModelSerializer):
#
#     class Meta:
#         model = User
#         fields = ["id", "username", "email", "Contact_number", "first_name", "last_name"]
#
#
# class CustomerSerializer(serializers.ModelSerializer):
#     customer = ParticularCustomerInfoSerializer(many=False, read_only=True)
#
#     class Meta:
#         model = CustomerInfo
#         fields = ["address", "total_sites", "customer"]
