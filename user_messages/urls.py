from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api.views import EnquiryViewSet, EnquiryMessageViewSet

# Create a router for the enquiry endpoints
router = DefaultRouter()
router.register(r'enquiries', EnquiryViewSet, basename='enquiry')

# URL patterns for the user_messages app
urlpatterns = [
    # Include the router URLs under /api/v1/messages/
    path('api/v1/messages/', include(router.urls)),
    
    # Nested messages endpoint for a specific enquiry
    path(
        'api/v1/messages/enquiries/<int:enquiry_id>/messages/',
        EnquiryMessageViewSet.as_view({
            'get': 'list',
            'post': 'create'
        }),
        name='enquiry-messages'
    ),
]