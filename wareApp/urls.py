from django.urls import include, path

from .views import create_newCustomer

# router may be optionally defined in `wareApp.views`; include it if present.
urlpatterns = []
try:
    from .views import router  # type: ignore

    urlpatterns.append(path("", include(router.urls)))
except Exception:
    # router not defined; skip router inclusion
    pass

urlpatterns.append(path("createCustomer/", create_newCustomer.as_view()))
