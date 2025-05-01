from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# Admin site configuration
admin.site.site_header = "Urban Tree Observatory"
admin.site.site_title = "UTO Admin"
admin.site.index_title = "Urban Tree Observatory Admin"


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/v1/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"
    ),
    # API endpoints
    path(
        "api/v1/",
        include(
            [
                # Authentication
                path(
                    "auth/",
                    include(
                        [
                            path(
                                "token/",
                                TokenObtainPairView.as_view(),
                                name="token_obtain_pair",
                            ),
                            path(
                                "token/refresh/",
                                TokenRefreshView.as_view(),
                                name="token_refresh",
                            ),
                        ]
                    ),
                ),
                # API endpoints
                path("", include("config.api_urls")),
            ]
        ),
    ),
    # Development tools
    path("api-auth/", include("rest_framework.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Debug toolbar
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]
