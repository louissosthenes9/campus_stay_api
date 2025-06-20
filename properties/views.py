from django.shortcuts import render
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import Q, Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import Properties, PropertyAmenity, Amenity
from .serializers import PropertySerializer

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

# Public search endpoint
class PropertySearchView(generics.ListAPIView):
    serializer_class = PropertySerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Properties.objects.filter(is_available=True).prefetch_related('amenities')
        
        # Get query parameters
        university = self.request.query_params.get('university')
        property_type = self.request.query_params.get('property_type')
        price_min = self.request.query_params.get('price_min')
        price_max = self.request.query_params.get('price_max')
        bedrooms = self.request.query_params.get('bedrooms')
        amenities = self.request.query_params.getlist('amenities')
        special_needs = self.request.query_params.get('special_needs')
        
        # Apply filters
        if university:
            # Filter by nearby university
            university_location = Point(float(university.split(',')[0]), float(university.split(',')[1]))
            queryset = queryset.filter(
                location__distance_lte=(university_location, D(km=5))
            )
            
        if property_type:
            queryset = queryset.filter(property_type=property_type)
            
        if price_min:
            queryset = queryset.filter(price__gte=float(price_min))
            
        if price_max:
            queryset = queryset.filter(price__lte=float(price_max))
            
        if bedrooms:
            queryset = queryset.filter(bedrooms=int(bedrooms))
            
        if amenities:
            queryset = queryset.filter(amenities__amenity__id__in=amenities)
            
        if special_needs:
            queryset = queryset.filter(is_special_needs=True)
            
        # Order by popularity (view count)
        return queryset.annotate(
            popularity=Count('view_count')
        ).order_by('-popularity', '-overall_score')

# Authenticated user endpoints
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_recently_viewed(request):
    user = request.user
    # Get properties viewed by the user in last 30 days
    recent_properties = Properties.objects.filter(
        view_count__gt=0,
        last_viewed__gte=(timezone.now() - timezone.timedelta(days=30))
    ).order_by('-last_viewed')[:10]
    
    serializer = PropertySerializer(recent_properties, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_favourites(request):
    user = request.user
    # Assuming you have a Favourite model in your favourites app
    from favourites.models import Favourite
    
    favourites = Favourite.objects.filter(user=user)
    properties = [f.property for f in favourites]
    
    serializer = PropertySerializer(properties, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def nearby_university_properties(request):
    user = request.user
    # Get user's preferred university location
    # Assuming you have a user profile with university preference
    from users.models import UserProfile
    try:
        profile = UserProfile.objects.get(user=user)
        university_location = profile.preferred_university_location
        
        # Get nearby properties
        nearby_properties = Properties.objects.filter(
            location__distance_lte=(university_location, D(km=5)),
            is_available=True
        ).order_by('distance')
        
        serializer = PropertySerializer(nearby_properties, many=True)
        return Response(serializer.data)
    except UserProfile.DoesNotExist:
        return Response(
            {'error': 'User profile not found'},
            status=status.HTTP_404_NOT_FOUND
        )

# Helper functions to get search filters
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_property_types(request):
    return Response(Properties.PROPERTY_TYPE_CHOICES)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_amenities(request):
    amenities = Amenity.objects.all()
    return Response([{'id': a.id, 'name': a.name} for a in amenities])

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_universities(request):
    from universities.models import University
    universities = University.objects.all()
    return Response([{
        'id': u.id,
        'name': u.name,
        'location': u.location
    } for u in universities])
