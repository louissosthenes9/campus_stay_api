from django.urls import path
from . import views

urlpatterns = [
    # Public endpoints
    path('search/', views.PropertySearchView.as_view(), name='property-search'),
    path('property-types/', views.get_property_types, name='property-types'),
    path('amenities/', views.get_amenities, name='amenities'),
    path('universities/', views.get_universities, name='universities'),
    
    # Authenticated user endpoints
    path('user/recently-viewed/', views.user_recently_viewed, name='user-recently-viewed'),
    path('user/favourites/', views.user_favourites, name='user-favourites'),
    path('user/nearby-university/', views.nearby_university_properties, name='nearby-university-properties'),
]
