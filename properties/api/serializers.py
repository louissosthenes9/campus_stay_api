from rest_framework import serializers
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from properties.models import Properties, PropertyAmenity, PropertyMedia, PropertyNearByPlaces, NearByPlaces, Amenity
from django.db import transaction
from drf_spectacular.utils import extend_schema_field
from typing import List, Optional


class PropertyMediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyMedia
        fields = ['id', 'media_type', 'url', 'display_order', 'is_primary', 'created_at']
    
    @extend_schema_field(serializers.URLField)
    def get_url(self, obj) -> Optional[str]:
        request = self.context.get('request')
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
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


class PropertiesSerializer(GeoFeatureModelSerializer):
    # Display fields
    property_type_display = serializers.CharField(source='get_property_type_display', read_only=True)
    windows_type_display = serializers.CharField(source='get_windows_type_display', read_only=True)
    electricity_type_display = serializers.CharField(source='get_electricity_type_display', read_only=True)
    
    # Related data
    amenities = PropertyAmenitySerializer(many=True, read_only=True)
    nearby_places = PropertyNearByPlacesSerializer(many=True, read_only=True)
    media = PropertyMediaSerializer(many=True, read_only=True)
    
    # Calculated fields
    distance_to_university = serializers.SerializerMethodField()
    
    # Separate image and video URLs for easier frontend handling
    images = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    
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
            'id', 'name', 'title', 'description', 
            'property_type', 'property_type_display', 'price', 'bedrooms',
            'toilets', 'address', 'available_from',
            'lease_duration', 'is_furnished', 'is_available',
            'is_fenced', 'windows_type', 'windows_type_display',
            'electricity_type', 'electricity_type_display',
            'water_supply', 'size', 'safety_score',
            'transportation_score', 'amenities_score',
            'overall_score', 'distance_to_university',
            'amenities', 'nearby_places', 'media',
            'images', 'videos', 'primary_image',
            'amenity_ids', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'location': {'required': False},  # Make location optional for easier testing
        }

    @extend_schema_field(serializers.ListField(child=serializers.URLField()))
    def get_images(self, obj) -> List[str]:
        """Get all image URLs"""
        images = obj.media.filter(media_type='image').order_by('display_order', 'created_at')
        request = self.context.get('request')
        if request:
            return [request.build_absolute_uri(img.file.url) for img in images]
        return [img.file.url for img in images]

    @extend_schema_field(serializers.ListField(child=serializers.URLField()))
    def get_videos(self, obj) -> List[str]:
        """Get all video URLs"""
        videos = obj.media.filter(media_type='video').order_by('display_order', 'created_at')
        request = self.context.get('request')
        if request:
            return [request.build_absolute_uri(vid.file.url) for vid in videos]
        return [vid.file.url for vid in videos]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_primary_image(self, obj) -> Optional[str]:
        """Get primary image URL"""
        primary_image = obj.media.filter(media_type='image', is_primary=True).first()
        if not primary_image:
            # Fallback to first image if no primary set
            primary_image = obj.media.filter(media_type='image').order_by('display_order', 'created_at').first()
        
        if primary_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(primary_image.file.url)
            return primary_image.file.url
        return None

    @extend_schema_field(serializers.FloatField(allow_null=True))
    def get_distance_to_university(self, obj) -> Optional[float]:
        """Calculate distance to user's university (for students only)"""
        request = self.context.get('request')
        if not (request and request.user.is_authenticated and getattr(request.user, 'roles', None) == 'student'):
            return None
        
        if not hasattr(request.user, 'student_profile'):
            return None
            
        university = getattr(request.user.student_profile, 'university', None)
        if not university:
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
        if value > 120:  # 10 years max
            raise serializers.ValidationError("Lease duration cannot exceed 120 months.")
        return value