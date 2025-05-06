from rest_framework import viewsets, permissions, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import PropertiesSerializer,PropertyAmenitySerializer,NearByPlacesSerializer, PropertyMediaSerializer,PropertyNearByPlacesSerializer
from properties.models import Properties, PropertyMedia, PropertyAmenity, PropertyNearByPlaces
from django.db import transaction

#custom permission class
class IsBrokerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.roles in ['broker', 'admin'] or 
            request.user.is_staff
        )


class PropertiesViewSet(viewsets.ModelViewSet):
    queryset = Properties.objects.all()
    serializer_class = PropertiesSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['property_type','broker','location','amenities','price', 'bedrooms', 'toilets', 'is_furnished',]    
    search_fields = ['title', 'description','address']
    ordering_fields = ['price','location']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = Properties.objects.filter(is_available=True)
        university_id = self.request.query_params.get('university_id')
        distance = self.request.query_params.get('distance', 5)  # Default 5km radius
        
        # If university_id is provided, filter properties by distance
        if university_id:
            from universities.models import University
            try:
                university = University.objects.get(id=university_id)
                queryset = queryset.annotate(
                    distance=Distance('location', university.location)
                ).filter(distance__lte=D(km=float(distance))).order_by('distance')
            except University.DoesNotExist:
                pass
            
        return queryset
    
    def get_permissions(self):
        """
        Override permissions:
        - Create/Update/Delete: Only brokers and admins
        - List/Retrieve: Any authenticated user
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsBrokerOrAdmin]
        return super().get_permissions()
    
    def perform_create(self, serializer):
        """Set the broker to the current user if they're a broker"""
        if self.request.user.roles == 'broker':
            serializer.save(broker=self.request.user)
        else:
            serializer.save()
    
    @action(detail=False, methods=['get'], url_path='near-university')
    def near_university(self, request):
        """Endpoint for students to find properties near their university"""
        if request.user.roles != 'student':
            return Response({"error": "This endpoint is only for students"}, 
                            status=status.HTTP_403_FORBIDDEN)
            
        try:
            # Get university ID from student's profile
            university_id = request.user.student_profile.university_id
            distance = request.query_params.get('distance', 5)  # Default 5km radius
            
            from universities.models import University
            try:
                university = University.objects.get(id=university_id)
                
                # Filter properties by distance to university
                properties = Properties.objects.filter(is_available=True).annotate(
                    distance=Distance('location', university.location)
                ).filter(distance__lte=D(km=float(distance))).order_by('distance')
                
                serializer = self.get_serializer(properties, many=True, context={'request': request})
                return Response(serializer.data)
            except University.DoesNotExist:
                return Response({"error": "University not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='my-properties')
    def my_properties(self, request):
        """Endpoint for brokers to list their properties"""
        if request.user.roles != 'broker':
            return Response({"error": "This endpoint is only for brokers"}, 
                            status=status.HTTP_403_FORBIDDEN)
        
        properties = Properties.objects.filter(broker=request.user)
        serializer = self.get_serializer(properties, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='register-property', permission_classes=[IsBrokerOrAdmin])
    def register_property(self, request):
        """Dedicated endpoint for brokers and admins to register new properties"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Set the broker to current user if they're a broker
            if request.user.roles == 'broker':
                serializer.save(broker=request.user)
            else:
                serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


