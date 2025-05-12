
from django.contrib import admin
from django.urls import path,include
from rest_framework.routers import DefaultRouter
from users.api.views import UserViewSet
from users.api.views import CustomTokenObtainPairView

from properties.api.views import PropertiesViewSet
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
    TokenBlacklistView,
    TokenObtainPairView
)

router = DefaultRouter()

router.register(r'users', UserViewSet)
router.register(r'properties', PropertiesViewSet)

urlpatterns = [
    path('api/v1/', include(router.urls)),
    path('api/v1/auth/token/',CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/v1/auth/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('admin/', admin.site.urls),
]
