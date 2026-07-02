from django.urls import path, include
from .views import *
from rest_framework import routers

#router = routers.DefaultRouter()
#router.register('tokens', TokenViewSet)

urlpatterns = [

    path('', include(router.urls)),
    path('createCustomer/',create_newCustomer.as_view())
]
