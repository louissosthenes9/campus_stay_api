import logging
from rest_framework import serializers
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.db.models import Avg
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from properties.models import Properties, PropertyAmenity, PropertyMedia, PropertyNearByPlaces, NearByPlaces, Amenity
from reviews.models import PropertyReviews  # Import the PropertyReviews model
from django.db import transaction
from drf_spectacular.utils import extend_schema_field
from typing import List, Optional


class PropertyMediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyMedia
        fields = ['id', 'media_type', 'url', 'thumbnail_url', 'display_order', 'is_primary', 'created_at']
    
    @extend_schema_field(serializers.URLField)
    def get_url(self, obj) -> Optional[str]:
        if not obj.file:
            return None
        
        # For Cloudinary, we can directly use the URL
        if hasattr(obj.file, 'url'):
            return obj.file.url
            
        # Fallback for non-Cloudinary storage
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return None
    
    @extend_schema_field(serializers.URLField)
    def get_thumbnail_url(self, obj) -> Optional[str]:
        if not obj.file or obj.media_type != 'image':
            return None
            
        try:
            # Generate a thumbnail URL with Cloudinary transformations
            if hasattr(obj.file, 'url'):
                # This adds Cloudinary transformations for a thumbnail
                base_url = obj.file.url
                # Add transformations: 300px width, auto height, auto quality, auto format
                if 'upload/' in base_url:
                    return base_url.replace('upload/', 'upload/w_300,h_200,c_fill,q_auto,f_auto/')
                return base_url
                
            # Fallback for non-Cloudinary storage
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating thumbnail URL: {str(e)}")
            
        return None


class PropertyAmenitySerializer(serializers.ModelSerializer):
    amenity_name = serializers.CharField(source='amenity.name', read_only=True)
    amenity_description = serializers.CharField(source='amenity.description', read_only=True)
    amenity_icon = serializers.CharField(source='amenity.icon', read_only=True)
    
    class Meta:
        model = PropertyAmenity
        fields = ['id', 'amenity', 'amenity_name', 'amenity_description', 'amenity_icon']


class NearByPlacesSerializer(GeoFeatureModelSerializer):
    place_type_display = serializers.CharField(source='get_place_type_display', read_only=True)

    class Meta:
        model = NearByPlaces
        geo_field = 'location'
        fields = ['id', 'name', 'place_type', 'place_type_display', 'address']


class PropertyNearByPlacesSerializer(serializers.ModelSerializer):
    place = NearByPlacesSerializer(read_only=True)
    
    class Meta:
        model = PropertyNearByPlaces
        fields = ['id', 'place', 'distance', 'walking_time']


# Simple review serializer for property details
class PropertyReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='user.get_full_name', read_only=True)
    reviewer_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = PropertyReviews
        fields = ['id', 'rating', 'comment', 'reviewer_name', 'reviewer_username', 'created_at']


class PropertiesSerializer(GeoFeatureModelSerializer):
    # Display fields
    property_type_display = serializers.CharField(source='get_property_type_display', read_only=True)
    windows_type_display = serializers.CharField(source='get_windows_type_display', read_only=True)
    electricity_type_display = serializers.CharField(source='get_electricity_type_display', read_only=True)
    
    # Related data
    amenities = PropertyAmenitySerializer(many=True, read_only=True)
    nearby_places = PropertyNearByPlacesSerializer(many=True, read_only=True)
    media = PropertyMediaSerializer(many=True, read_only=True)
    
    # Reviews data
    reviews = PropertyReviewSerializer(many=True, read_only=True)
    recent_reviews = serializers.SerializerMethodField()
    
    # Calculated fields
    distance_to_university = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    is_recently_viewed = serializers.SerializerMethodField()
    
    # Separate image and video URLs for easier frontend handling
    images = serializers.SerializerMethodField()
    image_thumbnails = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    primary_image_thumbnail = serializers.SerializerMethodField()
    
    # Write-only fields for creating/updating
    amenity_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )

    class Meta:
        model = Properties
        geo_field = 'location'
        fields = [
            'id', 'name', 'title', 'description', 'location',
            'property_type', 'property_type_display', 'price', 'bedrooms',
            'toilets', 'address', 'available_from',
            'lease_duration', 'is_furnished', 'is_available',
            'is_fenced', 'windows_type', 'windows_type_display',
            'electricity_type', 'electricity_type_display',
            'water_supply', 'size', 'safety_score',
            'transportation_score', 'amenities_score',
            'overall_score', 'distance_to_university',
            'amenities', 'nearby_places', 'media',
            'images', 'image_thumbnails', 'videos', 'primary_image', 'primary_image_thumbnail',
            'amenity_ids', 'created_at', 'updated_at',
            'is_special_needs', 'view_count', 'last_viewed',
            'average_rating', 'review_count', 'is_recently_viewed',
            'reviews', 'recent_reviews'
        ]
        extra_kwargs = {
            'location': {'required': False},  # Make location optional for easier testing
        }

    @extend_schema_field(serializers.ListField(child=PropertyReviewSerializer()))
    def get_recent_reviews(self, obj) -> List[dict]:
        """Get the 3 most recent reviews for the property"""
        recent_reviews = obj.reviews.select_related('user').order_by('-created_at')[:3]
        return PropertyReviewSerializer(recent_reviews, many=True).data

    @extend_schema_field(serializers.ListField(child=serializers.URLField()))
    def get_images(self, obj) -> List[str]:
        """Get all image URLs"""
        images = obj.media.filter(media_type='image').order_by('display_order', 'created_at')
        request = self.context.get('request')
        if request:
            return [img.file.url for img in images if img.file]  # Cloudinary URLs are already absolute
        return [img.file.url for img in images if img.file]  # Fallback

    @extend_schema_field(serializers.ListField(child=serializers.URLField()))
    def get_videos(self, obj) -> List[str]:
        """Get all video URLs"""
        videos = obj.media.filter(media_type='video').order_by('display_order', 'created_at')
        request = self.context.get('request')
        if request:
            return [request.build_absolute_uri(vid.file.url) for vid in videos if vid.file]
        return [vid.file.url for vid in videos if vid.file]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_primary_image(self, obj) -> Optional[str]:
        """Get primary image URL"""
        primary_image = obj.media.filter(media_type='image', is_primary=True).first()
        if not primary_image:
            # Fallback to first image if no primary set
            primary_image = obj.media.filter(media_type='image').order_by('display_order', 'created_at').first()
        
        if primary_image and primary_image.file:
            # Cloudinary URLs are already absolute
            return primary_image.file.url
        return None
        
    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_primary_image_thumbnail(self, obj) -> Optional[str]:
        """Get primary image thumbnail URL"""
        primary_image = obj.media.filter(media_type='image', is_primary=True).first()
        if not primary_image:
            # Fallback to first image if no primary set
            primary_image = obj.media.filter(media_type='image').order_by('display_order', 'created_at').first()
        
        if primary_image and primary_image.file and hasattr(primary_image.file, 'url'):
            # Generate thumbnail URL with Cloudinary transformations
            base_url = primary_image.file.url
            if 'upload/' in base_url:
                return base_url.replace('upload/', 'upload/w_600,h_400,c_fill,q_auto,f_auto/')
            return base_url
        return None
        
    @extend_schema_field(serializers.ListField(child=serializers.URLField()))
    def get_image_thumbnails(self, obj) -> List[str]:
        """Get all image thumbnail URLs"""
        images = obj.media.filter(media_type='image').order_by('display_order', 'created_at')
        thumbnails = []
        
        for img in images:
            if hasattr(img.file, 'url'):
                base_url = img.file.url
                if 'upload/' in base_url:
                    thumbnails.append(base_url.replace('upload/', 'upload/w_300,h_200,c_fill,q_auto,f_auto/'))
                else:
                    thumbnails.append(base_url)
        
        return thumbnails

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_distance_to_university(self, obj) -> Optional[float]:
        """Calculate distance to user's university (for students only)"""
        request = self.context.get('request')
        if not (request and request.user.is_authenticated and getattr(request.user, 'roles', None) == 'student'):
            return None
        
        if not hasattr(request.user, 'student_profile'):
            return None
            
        university = getattr(request.user.student_profile, 'university', None)
        if not university or not university.location:
            return None
        
        try:
            distance_obj = Properties.objects.filter(id=obj.id).annotate(
                dist=Distance('location', university.location)
            ).values('dist').first()
            
            if distance_obj and distance_obj['dist'] is not None:
                return round(distance_obj['dist'].m / 1000, 2)  # Convert to kilometers
        except Exception:
            pass
        
        return None

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_average_rating(self, obj) -> Optional[float]:
        """Get average rating from PropertyReviews."""
        try:
            avg_rating = obj.reviews.aggregate(rating_avg=Avg('rating'))['rating_avg']
            return round(avg_rating, 1) if avg_rating else None
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error calculating average rating: {str(e)}")
            return None
    
    @extend_schema_field(serializers.IntegerField())
    def get_review_count(self, obj) -> int:
        """Get total number of PropertyReviews."""
        try:
            return obj.reviews.count()
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting review count: {str(e)}")
            return 0
    
    @extend_schema_field(serializers.BooleanField())
    def get_is_recently_viewed(self, obj) -> bool:
        """Check if property is in user's recently viewed list."""
        request = self.context.get('request')
        if request and request.session:
            viewed_properties = request.session.get('recently_viewed_properties', [])
            return obj.id in viewed_properties
        return False

    @transaction.atomic
    def create(self, validated_data):
        """Create property with amenities"""
        amenity_ids = validated_data.pop('amenity_ids', [])
        
        # Create the property
        property_instance = Properties.objects.create(**validated_data)
        
        # Add amenities - Remove duplicates and use get_or_create
        if amenity_ids:
            unique_amenity_ids = list(set(amenity_ids))  # Remove duplicates
            for amenity_id in unique_amenity_ids:
                try:
                    PropertyAmenity.objects.get_or_create(
                        property=property_instance,
                        amenity_id=amenity_id
                    )
                except Exception:
                    # Skip invalid amenity IDs
                    pass
        
        return property_instance

    @transaction.atomic
    def update(self, instance, validated_data):
        """Update property and handle amenities"""
        amenity_ids = validated_data.pop('amenity_ids', None)
        
        # Update property fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update amenities if provided
        if amenity_ids is not None:
            # Remove existing amenities
            instance.amenities.all().delete()
            
            # Add new amenities - Remove duplicates first
            unique_amenity_ids = list(set(amenity_ids))  # Remove duplicates
            for amenity_id in unique_amenity_ids:
                try:
                    PropertyAmenity.objects.get_or_create(
                        property=instance,
                        amenity_id=amenity_id
                    )
                except Exception:
                    # Skip invalid amenity IDs
                    pass
        
        return instance

    def validate_amenity_ids(self, value):
        """Validate that all amenity IDs exist and remove duplicates"""
        if value:
            # Remove duplicates from input
            unique_ids = list(set(value))
            existing_ids = set(Amenity.objects.filter(id__in=unique_ids).values_list('id', flat=True))
            invalid_ids = set(unique_ids) - existing_ids
            if invalid_ids:
                raise serializers.ValidationError(
                    f"Invalid amenity IDs: {list(invalid_ids)}"
                )
            return unique_ids  # Return the deduplicated list
        return value

    def validate_price(self, value):
        """Validate price is positive"""
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def validate_bedrooms(self, value):
        """Validate bedrooms count"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Bedrooms cannot be negative.")
        return value

    def validate_toilets(self, value):
        """Validate toilets count"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Toilets cannot be negative.")
        return value

    def validate_lease_duration(self, value):
        """Validate lease duration"""
        if value < 1:
            raise serializers.ValidationError("Lease duration must be at least 1 month.")
        if value > 120: 
            raise serializers.ValidationError("Lease duration cannot exceed 120 months.")
        return value


# Lightweight serializer for property lists (without full review data)
class PropertiesListSerializer(GeoFeatureModelSerializer):
    """Lighter version of PropertiesSerializer for list views"""
    property_type_display = serializers.CharField(source='get_property_type_display', read_only=True)
    primary_image = serializers.SerializerMethodField()
    primary_image_thumbnail = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    distance_to_university = serializers.SerializerMethodField()

    class Meta:
        model = Properties
        geo_field = 'location'
        fields = [
            'id', 'name', 'title', 'price', 'bedrooms', 'toilets',
            'address', 'property_type', 'property_type_display',
            'is_furnished', 'is_available', 'primary_image', 'primary_image_thumbnail',
            'average_rating', 'review_count', 'distance_to_university',
            'overall_score', 'created_at'
        ]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_primary_image(self, obj) -> Optional[str]:
        """Get primary image URL"""
        primary_image = obj.media.filter(media_type='image', is_primary=True).first()
        if not primary_image:
            primary_image = obj.media.filter(media_type='image').order_by('display_order', 'created_at').first()
        
        if primary_image and primary_image.file:
            return primary_image.file.url
        return None
        
    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_primary_image_thumbnail(self, obj) -> Optional[str]:
        """Get primary image thumbnail URL"""
        primary_image = obj.media.filter(media_type='image', is_primary=True).first()
        if not primary_image:
            primary_image = obj.media.filter(media_type='image').order_by('display_order', 'created_at').first()
        
        if primary_image and primary_image.file and hasattr(primary_image.file, 'url'):
            base_url = primary_image.file.url
            if 'upload/' in base_url:
                return base_url.replace('upload/', 'upload/w_300,h_200,c_fill,q_auto,f_auto/')
            return base_url
        return None

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_average_rating(self, obj) -> Optional[float]:
        """Get average rating from PropertyReviews."""
        try:
            avg_rating = obj.reviews.aggregate(rating_avg=Avg('rating'))['rating_avg']
            return round(avg_rating, 1) if avg_rating else None
        except Exception:
            return None
    
    @extend_schema_field(serializers.IntegerField())
    def get_review_count(self, obj) -> int:
        """Get total number of PropertyReviews."""
        try:
            return obj.reviews.count()
        except Exception:
            return 0

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_distance_to_university(self, obj) -> Optional[float]:
        """Calculate distance to user's university (for students only)"""
        request = self.context.get('request')
        if not (request and request.user.is_authenticated and getattr(request.user, 'roles', None) == 'student'):
            return None
        
        if not hasattr(request.user, 'student_profile'):
            return None
            
        university = getattr(request.user.student_profile, 'university', None)
        if not university or not university.location:
            return None
        
        try:
            distance_obj = Properties.objects.filter(id=obj.id).annotate(
                dist=Distance('location', university.location)
            ).values('dist').first()
            
            if distance_obj and distance_obj['dist'] is not None:
                return round(distance_obj['dist'].m / 1000, 2)  # Convert to kilometers
        except Exception:
            pass
        
        return None