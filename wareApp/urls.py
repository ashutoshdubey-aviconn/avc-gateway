from django.urls import include, path

# flake8: noqa
from .views import *  # noqa: F403,F405

# router = routers.DefaultRouter()
# router.register('tokens', TokenViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("createCustomer/", create_newCustomer.as_view()),
]
