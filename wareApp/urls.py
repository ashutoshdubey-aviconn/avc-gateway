from django.urls import include, path

from .views import *

# router = routers.DefaultRouter()
# router.register('tokens', TokenViewSet)

urlpatterns = [path("", include(router.urls)), path("createCustomer/", create_newCustomer.as_view())]
