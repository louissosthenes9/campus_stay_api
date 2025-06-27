from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.openapi import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from properties.models import Properties, PropertyAmenity, PropertyMedia
from universities.models import University
from .serializers import PropertiesSerializer

import json
import logging

logger = logging.getLogger(__name__)

@extend_schema_view(
    list=extend_schema(
        description="List all available properties with optional filtering.",
        parameters=[
            OpenApiParameter(
                name="university_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Filter properties near a specific university.",
            ),
            OpenApiParameter(
                name="distance",
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
                description="Maximum distance from university in kilometers (default: 5).",
            ),
        ],
    ),
    create=extend_schema(description="Create a new property with media and amenities."),
    retrieve=extend_schema(description="Retrieve detailed information about a specific property."),
    update=extend_schema(description="Update property information, media, and amenities."),
    partial_update=extend_schema(description="Partially update property information."),
    destroy=extend_schema(description="Delete a property."),
)
class PropertiesViewSet(viewsets.ModelViewSet):
    """ViewSet for managing property CRUD operations with media and proximity filtering."""
    
    queryset = Properties.objects.prefetch_related(
        'reviews__reviewer',  # Changed from 'reviews__user' to 'reviews__reviewer'
        'media',
        'amenities__amenity'
    )
    serializer_class = PropertiesSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["property_type", "price", "bedrooms", "toilets", "is_furnished"]
    search_fields = ["title", "description", "address"]
    ordering_fields = ["price", "created_at"]
    ordering = ["-created_at"]

    # Custom Actions
    @action(detail=False, methods=["get"], url_path="marketing-categories")
    def marketing_categories(self, request):
        """Retrieve properties categorized for marketing page display."""
        try:
            limit = int(request.query_params.get("limit", 6))
            distance_km = float(request.query_params.get("distance", 5))
            
            categories = {
                "cheap": [],
                "near_university": [],
                "top_rated": [],
                "special_needs": [],
                "popular": [],
            }
            
            # Base queryset for available properties
            base_queryset = Properties.objects.filter(is_available=True)
            
            # Cheap properties (60,000 to 90,000)
            cheap_properties = base_queryset.filter(
                price__gte=60000, price__lte=90000
            ).order_by("price")[:limit]
            categories["cheap"] = self.get_serializer(
                cheap_properties, many=True, context={"request": request}
            ).data
            
            # Top-rated properties (using reviews)
            from django.db.models import Avg, Count
            top_rated_properties = (
                base_queryset.annotate(
                    avg_rating=Avg('reviews__rating'),
                    review_count=Count('reviews')
                )
                .filter(review_count__gt=0)
                .order_by('-avg_rating', '-review_count')[:limit]
            )
            categories["top_rated"] = self.get_serializer(
                top_rated_properties, many=True, context={"request": request}
            ).data
            
            # Special needs properties (wheelchair accessible)
            special_needs_properties = base_queryset.filter(
                is_special_needs=True
            ).order_by("-created_at")[:limit]
            categories["special_needs"] = self.get_serializer(
                special_needs_properties, many=True, context={"request": request}
            ).data
            
            # Popular properties (based on view count)
            popular_properties = base_queryset.order_by("-view_count")[:limit]
            categories["popular"] = self.get_serializer(
                popular_properties, many=True, context={"request": request}
            ).data
            
            # Near university properties
            near_university_properties = []
            if request.user.is_authenticated:
                try:
                    if (
                        hasattr(request.user, "roles")
                        and request.user.roles == "student"
                        and hasattr(request.user, "student_profile")
                        and request.user.student_profile.university_id
                    ):
                        university = University.objects.get(
                            id=request.user.student_profile.university_id
                        )
                        near_university_properties = base_queryset.annotate(
                            distance=Distance("location", university.location)
                        ).filter(distance__lte=D(km=distance_km)).order_by("distance")[:limit]
                    
                    elif not near_university_properties:
                        popular_university = University.objects.first()
                        if popular_university:
                            near_university_properties = base_queryset.annotate(
                                distance=Distance("location", popular_university.location)
                            ).filter(distance__lte=D(km=distance_km)).order_by("distance")[:limit]
                except University.DoesNotExist:
                    logger.warning(f"University not found for user {request.user.id}")
                except Exception as e:
                    logger.error(f"Error fetching near-university properties: {str(e)}")
            
            categories["near_university"] = self.get_serializer(
                near_university_properties, many=True, context={"request": request}
            ).data
            
            return Response(categories)
        except Exception as e:
            logger.error(f"Error in marketing_categories: {str(e)}", exc_info=True)
            raise

    # Queryset Customization
    def get_queryset(self):
        """Filter queryset, optionally by university proximity."""
        queryset = Properties.objects.filter(is_available=True)
        university_id = self.request.query_params.get("university_id")
        distance = self.request.query_params.get("distance", 5)

        if university_id:
            try:
                university = University.objects.get(id=university_id)
                queryset = (
                    queryset.annotate(distance=Distance("location", university.location))
                    .filter(distance__lte=D(km=float(distance)))
                    .order_by("distance")
                )
            except University.DoesNotExist:
                logger.warning(f"University {university_id} not found")
                return Properties.objects.none()
            except Exception as e:
                logger.error(f"Error filtering properties by university {university_id}: {str(e)}", exc_info=True)
                raise
        return queryset

    # Create Operations
    def create(self, request, *args, **kwargs):
        """Create a new property with associated media and amenities."""
        logger.info(f"==== Incoming Property Create Request ====\n"
                    f"User: {request.user.id}\n"
                    f"Data: {dict(request.data)}\n"
                    f"Files: {{k: [f.name for f in v] for k, v in request.FILES.lists()}}\n"
                    f"Headers: {{k: v for k, v in request.META.items() if k.startswith('HTTP_')}}")

        try:
            with transaction.atomic():
                # Extract files and property data
                images = request.FILES.getlist("images", [])
                videos = request.FILES.getlist("videos", [])
                property_data = {
                    key: value for key, value in request.data.items() if key not in ["images", "videos"]
                }

                # Parse JSON fields
                if "amenity_ids" in property_data and isinstance(property_data["amenity_ids"], str):
                    try:
                        property_data["amenity_ids"] = json.loads(property_data["amenity_ids"])
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse amenity_ids JSON: {str(e)}")
                        return Response(
                            {"amenity_ids": "Invalid JSON format"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                
                if "location" in property_data and isinstance(property_data["location"], str):
                    try:
                        property_data["location"] = json.loads(property_data["location"])
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON format for location: {property_data['location']}")
                        return Response(
                            {"location": "Invalid JSON format"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                # Create property
                serializer = self.get_serializer(data=property_data)
                serializer.is_valid(raise_exception=True)
                property_instance = serializer.save()
                logger.info(f"Property instance created: {property_instance.id}")

                # Handle amenities
                if "amenity_ids" in property_data and property_data["amenity_ids"]:
                    for amenity_id in property_data["amenity_ids"]:
                        try:
                            PropertyAmenity.objects.get_or_create(
                                property=property_instance, amenity_id=amenity_id
                            )
                        except Exception as e:
                            logger.error(f"Error adding amenity {amenity_id} to property {property_instance.id}: {str(e)}")
                            raise

                # Handle image uploads with Cloudinary
                for i, image in enumerate(images):
                    try:
                        # Create the media instance - Cloudinary will handle the upload
                        media_instance = PropertyMedia.objects.create(
                            property=property_instance,
                            media_type="image",
                            file=image,
                            display_order=i,
                            is_primary=(i == 0),
                        )
                        
                        # Log successful upload
                        logger.info(f"Image uploaded to Cloudinary - ID: {media_instance.id}")
                        logger.info(f"File name: {image.name}")
                        logger.info(f"Cloudinary URL: {media_instance.file.url}")
                        logger.info(f"File size: {image.size}")
                        
                    except Exception as e:
                        logger.error(f"Error uploading image {image.name} to Cloudinary: {str(e)}")
                        raise

                # Handle video uploads with Cloudinary
                for i, video in enumerate(videos, start=len(images)):  # Continue display order after images
                    try:
                        # Create the media instance - Cloudinary will handle the upload
                        media_instance = PropertyMedia.objects.create(
                            property=property_instance,
                            media_type="video",
                            file=video,
                            display_order=i,
                        )
                        
                        # Log successful upload
                        logger.info(f"Video uploaded to Cloudinary - ID: {media_instance.id}")
                        logger.info(f"File name: {video.name}")
                        logger.info(f"Cloudinary URL: {media_instance.file.url}")
                        logger.info(f"File size: {video.size}")
                        
                    except Exception as e:
                        logger.error(f"Error uploading video {video.name} to Cloudinary: {str(e)}")
                        raise

                # Prepare response
                response_serializer = self.get_serializer(property_instance, context={"request": request})
                logger.info(f"Property created successfully: {property_instance.id}")
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating property for user {request.user.id}: {str(e)}", exc_info=True)
            raise

    # Update Operations
    def update(self, request, *args, **kwargs):
        """Update a property with associated media and amenities."""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        logger.info(f"Updating property {instance.id} by user {request.user.id}")

        try:
            with transaction.atomic():
                # Extract files and property data
                images = request.FILES.getlist("images", [])
                videos = request.FILES.getlist("videos", [])
                property_data = {
                    key: value for key, value in request.data.items() if key not in ["images", "videos", "replace_media"]
                }

                # Parse JSON fields
                if "amenity_ids" in property_data and isinstance(property_data["amenity_ids"], str):
                    try:
                        property_data["amenity_ids"] = json.loads(property_data["amenity_ids"])
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse amenity_ids JSON: {str(e)}")

                # Update property
                serializer = self.get_serializer(instance, data=property_data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                logger.info(f"Property data updated: {instance.id}")

                # Handle media replacement
                replace_media = request.data.get("replace_media", "false").lower() == "true"
                if replace_media:
                    try:
                        instance.media.all().delete()
                        logger.info(f"Existing media deleted for property {instance.id}")
                    except Exception as e:
                        logger.error(f"Error deleting media for property {instance.id}: {str(e)}")
                        raise

                # Add new images with Cloudinary
                existing_images = instance.media.filter(media_type="image").order_by('-display_order').first()
                existing_count = existing_images.display_order + 1 if existing_images else 0
                
                for i, image in enumerate(images, start=existing_count):
                    try:
                        # Create the media instance - Cloudinary will handle the upload
                        media_instance = PropertyMedia.objects.create(
                            property=instance,
                            media_type="image",
                            file=image,
                            display_order=i,
                            is_primary=(existing_count == 0 and i == 0),  # Set as primary if first image
                        )
                        
                        logger.info(f"Image uploaded to Cloudinary - ID: {media_instance.id}")
                        logger.info(f"File name: {image.name}")
                        logger.info(f"Cloudinary URL: {media_instance.file.url}")
                        
                    except Exception as e:
                        logger.error(f"Error uploading image {image.name} to Cloudinary: {str(e)}")
                        raise

                # Add new videos with Cloudinary
                existing_videos = instance.media.filter(media_type="video").order_by('-display_order').first()
                video_start = existing_videos.display_order + 1 if existing_videos else (existing_count + len(images))
                
                for i, video in enumerate(videos, start=video_start):
                    try:
                        # Create the media instance - Cloudinary will handle the upload
                        media_instance = PropertyMedia.objects.create(
                            property=instance,
                            media_type="video",
                            file=video,
                            display_order=i,
                        )
                        
                        logger.info(f"Video uploaded to Cloudinary - ID: {media_instance.id}")
                        logger.info(f"File name: {video.name}")
                        logger.info(f"Cloudinary URL: {media_instance.file.url}")
                        
                    except Exception as e:
                        logger.error(f"Error uploading video {video.name} to Cloudinary: {str(e)}")
                        raise

                # Update amenities
                if "amenity_ids" in property_data:
                    try:
                        instance.amenities.all().delete()
                        amenity_ids = property_data["amenity_ids"]
                        if isinstance(amenity_ids, list):
                            unique_amenity_ids = list(set(amenity_ids))
                            for amenity_id in unique_amenity_ids:
                                PropertyAmenity.objects.get_or_create(
                                    property=instance, amenity_id=amenity_id
                                )
                        logger.info(f"Amenities updated for property {instance.id}")
                    except Exception as e:
                        logger.error(f"Error updating amenities for property {instance.id}: {str(e)}")
                        raise

                response_serializer = self.get_serializer(instance, context={"request": request})
                logger.info(f"Property updated successfully: {instance.id}")
                return Response(response_serializer.data)
        except Exception as e:
            logger.error(f"Error updating property {instance.id} for user {request.user.id}: {str(e)}", exc_info=True)
            raise

    # Media Management Actions
    @extend_schema(
        description="Add media files to an existing property.",
        parameters=[
            OpenApiParameter(
                name="images",
                type=OpenApiTypes.BINARY,
                location=OpenApiParameter.QUERY,
                description="Image files to upload.",
                many=True,
            ),
            OpenApiParameter(
                name="videos",
                type=OpenApiTypes.BINARY,
                location=OpenApiParameter.QUERY,
                description="Video files to upload.",
                many=True,
            ),
        ],
    )
    @action(detail=True, methods=["post"], url_path="add-media")
    def add_media(self, request, pk=None):
        """Add media files to an existing property."""
        property_instance = self.get_object()
        images = request.FILES.getlist("images", [])
        videos = request.FILES.getlist("videos", [])

        if not images and not videos:
            logger.warning(f"No media files provided for property {property_instance.id} by user {request.user.id}")
            return Response({"error": "No media files provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Add images with Cloudinary
                existing_images = property_instance.media.filter(media_type="image").order_by('-display_order').first()
                existing_count = existing_images.display_order + 1 if existing_images else 0
                
                for i, image in enumerate(images, start=existing_count):
                    try:
                        # Create the media instance - Cloudinary will handle the upload
                        media_instance = PropertyMedia.objects.create(
                            property=property_instance,
                            media_type="image",
                            file=image,
                            display_order=i,
                            is_primary=(existing_count == 0 and i == 0),  # Set as primary if first image
                        )
                        
                        logger.info(f"Image added to Cloudinary - ID: {media_instance.id}")
                        logger.info(f"File name: {image.name}")
                        logger.info(f"Cloudinary URL: {media_instance.file.url}")
                        
                    except Exception as e:
                        logger.error(f"Error uploading image {image.name} to Cloudinary: {str(e)}")
                        raise

                # Add videos with Cloudinary
                existing_videos = property_instance.media.filter(media_type="video").order_by('-display_order').first()
                video_start = existing_videos.display_order + 1 if existing_videos else (existing_count + len(images))
                
                for i, video in enumerate(videos, start=video_start):
                    try:
                        # Create the media instance - Cloudinary will handle the upload
                        media_instance = PropertyMedia.objects.create(
                            property=property_instance,
                            media_type="video",
                            file=video,
                            display_order=i,
                        )
                        
                        logger.info(f"Video added to Cloudinary - ID: {media_instance.id}")
                        logger.info(f"File name: {video.name}")
                        logger.info(f"Cloudinary URL: {media_instance.file.url}")
                        
                    except Exception as e:
                        logger.error(f"Error uploading video {video.name} to Cloudinary: {str(e)}")
                        raise

                serializer = self.get_serializer(property_instance, context={"request": request})
                logger.info(f"Media added to property {property_instance.id} by user {request.user.id}")
                return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error adding media to property {property_instance.id} by user {request.user.id}: {str(e)}", exc_info=True)
            raise

    @extend_schema(
        description="Remove specific media from a property.",
        parameters=[
            OpenApiParameter(
                name="media_id",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="ID of the media file to remove.",
            ),
        ],
    )
    @action(detail=True, methods=["delete"], url_path=r"remove-media/(?P<media_id>[^/.]+)")
    def remove_media(self, request, pk=None, media_id=None):
        """Remove specific media from a property."""
        property_instance = self.get_object()

        try:
            media = PropertyMedia.objects.get(id=media_id, property=property_instance)
            media.delete()
            logger.info(f"Media {media_id} removed from property {property_instance.id} by user {request.user.id}")
            return Response({"message": "Media removed successfully"})
        except PropertyMedia.DoesNotExist:
            logger.warning(f"Media {media_id} not found for property {property_instance.id} by user {request.user.id}")
            return Response({"error": "Media not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error removing media {media_id} from property {property_instance.id}: {str(e)}", exc_info=True)
            return Response({"error": "Failed to remove media"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Student-Specific Actions
    @extend_schema(
        description="Retrieve properties near a student's university.",
        parameters=[
            OpenApiParameter(
                name="distance",
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
                description="Maximum distance from university in kilometers (default: 5).",
            ),
        ],
    )
    @action(detail=False, methods=["get"], url_path="near-university")
    def near_university(self, request):
        """Retrieve properties near the student's university."""
        if request.user.roles != "student":
            logger.warning(f"Non-student user {request.user.id} attempted to access near-university endpoint")
            return Response({"error": "This endpoint is only for students"}, status=status.HTTP_403_FORBIDDEN)

        if not hasattr(request.user, "student_profile") or not request.user.student_profile.university_id:
            logger.warning(f"Student profile or university not set for user {request.user.id}")
            return Response({"error": "Student profile or university not set"}, status=status.HTTP_400_BAD_REQUEST)

        university_id = request.user.student_profile.university_id
        distance = request.query_params.get("distance", 5)

        try:
            university = University.objects.get(id=university_id)
            properties = (
                Properties.objects.filter(is_available=True)
                .annotate(distance=Distance("location", university.location))
                .filter(distance__lte=D(km=float(distance)))
                .order_by("distance")
            )
            serializer = self.get_serializer(properties, many=True, context={"request": request})
            logger.info(f"Retrieved {properties.count()} properties near university {university_id} for student {request.user.id}")
            return Response(serializer.data)
        except University.DoesNotExist:
            logger.warning(f"University {university_id} not found for student {request.user.id}")
            return Response({"error": "University not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error retrieving properties near university {university_id} for user {request.user.id}: {str(e)}", exc_info=True)
            return Response({"error": "An unexpected error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)