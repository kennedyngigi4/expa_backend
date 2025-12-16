from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),

    # accounts urls
    path( 'api/account/', include("apps.accounts.urls")),
    path( 'api/account/superadmin/', include("apps.accounts.superadmin.urls")),
    path( 'api/account/partnershop/', include("apps.accounts.partnershop.urls")),


    # Drivers-riders
    path("api/drivers/", include("apps.drivers.urls")),


    # deliveries urls
    path( 'api/deliveries/', include("apps.deliveries.urls")),
    path( 'api/deliveries/superadmin/', include("apps.deliveries.superadmin.urls")),
    path( 'api/deliveries/manager/', include("apps.deliveries.manager.urls")),
    path( 'api/deliveries/partnershop/', include("apps.deliveries.partnershop.urls")),
    path( 'api/deliveries/drivers/', include("apps.deliveries.drivers.urls")),


    # corporate urls
    path( "api/corporate/", include("apps.corporate.urls")),


    # Full loads urls
    path( "api/fullloads/", include("apps.fullloads.urls")),
    path( "api/fullloads/manager/", include("apps.fullloads.manager.urls")),

    #International orders
    path( "api/international/", include("apps.international.urls")),

    # messaging urls
    path( "api/messaging/", include("apps.messaging.urls")),
    path( "api/messaging/partnershop/", include("apps.messaging.partnershop.urls")),

    # payments urls
    path( "api/payments/", include("apps.payments.urls")),
    path( "api/payments/superadmin/", include("apps.payments.superadmin.urls")),
]


urlpatterns += static( settings.STATIC_URL, document_root=settings.STATIC_ROOT )
urlpatterns += static( settings.MEDIA_URL, document_root=settings.MEDIA_ROOT )
