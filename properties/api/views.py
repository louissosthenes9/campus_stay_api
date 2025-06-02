from rest_framework import viewsets, permissions, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .serializers import PropertiesSerializer
from properties.models import Properties, PropertyMedia, PropertyAmenity
from universities.models import University
from django.db import transaction
import json


class PropertiesViewSet(viewsets.ModelViewSet):
    queryset = Properties.objects.all()
    serializer_class = PropertiesSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]  # Enable file uploads
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['property_type', 'price', 'bedrooms', 'toilets', 'is_furnished',]
    search_fields = ['title', 'description', 'address']
    ordering_fields = ['price', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = Properties.objects.filter(is_available=True)
        university_id = self.request.query_params.get('university_id')
        distance = self.request.query_params.get('distance', 5)
        
        if university_id:
            try:
                university = University.objects.get(id=university_id)
                queryset = queryset.annotate(
                    distance=Distance('location', university.location)
                ).filter(distance__lte=D(km=float(distance))).order_by('distance')
            except University.DoesNotExist:
                return Properties.objects.none()
        return queryset

    def create(self, request, *args, **kwargs):
        """Handle property creation with images and videos in a single request"""
        with transaction.atomic():
            # Extract files from request
            images = request.FILES.getlist('images', [])
            videos = request.FILES.getlist('videos', [])
            
            # Handle JSON data that might be sent as form data
            property_data = {}
            for key, value in request.data.items():
                if key not in ['images', 'videos']:
                    property_data[key] = value
            
            # Handle amenity_ids if sent as JSON string
            if 'amenity_ids' in property_data:
                if isinstance(property_data['amenity_ids'], str):
                    try:
                        property_data['amenity_ids'] = json.loads(property_data['amenity_ids'])
                    except json.JSONDecodeError:
                        pass
            
            # Create property instance
            serializer = self.get_serializer(data=property_data)
            serializer.is_valid(raise_exception=True)
            property_instance = serializer.save()
            
            # Handle amenities
            if 'amenity_ids' in property_data and property_data['amenity_ids']:
                amenity_ids = property_data['amenity_ids']
                if isinstance(amenity_ids, list):
                    for amenity_id in amenity_ids:
                        PropertyAmenity.objects.create(
                            property=property_instance,
                            amenity_id=amenity_id
                        )
            
            # Handle image uploads
            for i, image in enumerate(images):
                PropertyMedia.objects.create(
                    property=property_instance,
                    media_type='image',
                    file=image,
                    display_order=i,
                    is_primary=(i == 0)  # First image as primary
                )
            
            # Handle video uploads
            for i, video in enumerate(videos):
                PropertyMedia.objects.create(
                    property=property_instance,
                    media_type='video',
                    file=video,
                    display_order=i
                )
            
            # Return the created property with all related data
            response_serializer = self.get_serializer(
                property_instance, 
                context={'request': request}
            )
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Handle property updates with media files"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        with transaction.atomic():
            # Extract files from request
            images = request.FILES.getlist('images', [])
            videos = request.FILES.getlist('videos', [])
            
            # Handle property data update
            property_data = {}
            for key, value in request.data.items():
                if key not in ['images', 'videos', 'replace_media']:
                    property_data[key] = value
            
            # Handle amenity_ids if sent as JSON string
            if 'amenity_ids' in property_data:
                if isinstance(property_data['amenity_ids'], str):
                    try:
                        property_data['amenity_ids'] = json.loads(property_data['amenity_ids'])
                    except json.JSONDecodeError:
                        pass
            
            serializer = self.get_serializer(instance, data=property_data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            # Handle media replacement vs addition
            replace_media = request.data.get('replace_media', 'false').lower() == 'true'
            
            if replace_media:
                # Delete existing media
                instance.media.all().delete()
            
            # Add new images
            existing_images_count = instance.media.filter(media_type='image').count()
            for i, image in enumerate(images):
                PropertyMedia.objects.create(
                    property=instance,
                    media_type='image',
                    file=image,
                    display_order=existing_images_count + i,
                    is_primary=(existing_images_count == 0 and i == 0)
                )
            
            # Add new videos
            existing_videos_count = instance.media.filter(media_type='video').count()
            for i, video in enumerate(videos):
                PropertyMedia.objects.create(
                    property=instance,
                    media_type='video',
                    file=video,
                    display_order=existing_videos_count + i
                )
            
            # Update amenities if provided
            if 'amenity_ids' in property_data:
                instance.amenities.all().delete()  # Remove existing
                amenity_ids = property_data['amenity_ids']
                if isinstance(amenity_ids, list):
                    for amenity_id in amenity_ids:
                        PropertyAmenity.objects.create(
                            property=instance,
                            amenity_id=amenity_id
                        )
            
            response_serializer = self.get_serializer(
                instance, 
                context={'request': request}
            )
            return Response(response_serializer.data)

    @action(detail=True, methods=['post'], url_path='add-media')
    def add_media(self, request, pk=None):
        """Endpoint specifically for adding media to existing property"""
        property_instance = self.get_object()
        
        images = request.FILES.getlist('images', [])
        videos = request.FILES.getlist('videos', [])
        
        if not images and not videos:
            return Response(
                {"error": "No media files provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Add images
            existing_images_count = property_instance.media.filter(media_type='image').count()
            for i, image in enumerate(images):
                PropertyMedia.objects.create(
                    property=property_instance,
                    media_type='image',
                    file=image,
                    display_order=existing_images_count + i,
                    is_primary=(existing_images_count == 0 and i == 0)
                )
            
            # Add videos
            existing_videos_count = property_instance.media.filter(media_type='video').count()
            for i, video in enumerate(videos):
                PropertyMedia.objects.create(
                    property=property_instance,
                    media_type='video',
                    file=video,
                    display_order=existing_videos_count + i
                )
        
        serializer = self.get_serializer(property_instance, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['delete'], url_path='remove-media/(?P<media_id>[^/.]+)')
    def remove_media(self, request, pk=None, media_id=None):
        """Remove specific media from property"""
        property_instance = self.get_object()
        
        try:
            media = PropertyMedia.objects.get(
                id=media_id, 
                property=property_instance
            )
            media.delete()
            return Response({"message": "Media removed successfully"})
        except PropertyMedia.DoesNotExist:
            return Response(
                {"error": "Media not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='near-university')
    def near_university(self, request):
        if request.user.roles != 'student':
            return Response(
                {"error": "This endpoint is only for students"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not hasattr(request.user, 'student_profile') or not request.user.student_profile.university_id:
            return Response(
                {"error": "Student profile or university not set"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        university_id = request.user.student_profile.university_id
        distance = request.query_params.get('distance', 5)
        
        try:
            university = University.objects.get(id=university_id)
            properties = Properties.objects.filter(is_available=True).annotate(
                distance=Distance('location', university.location)
            ).filter(distance__lte=D(km=float(distance))).order_by('distance')
            
            serializer = self.get_serializer(
                properties, 
                many=True, 
                context={'request': request}
            )
            return Response(serializer.data)
        except University.DoesNotExist:
            return Response(
                {"error": "University not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )