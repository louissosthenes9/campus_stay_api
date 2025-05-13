from rest_framework import serializers
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from properties.models import (
    Properties,
    PropertyAmenity,
    PropertyMedia,
    PropertyNearByPlaces,
    NearByPlaces,
    Amenity
)


class NearByPlacesSerializer(GeoFeatureModelSerializer):
    place_type_display = serializers.CharField(
        source='get_place_type_display',
        read_only=True
    )

    class Meta:
        model = NearByPlaces
        geo_field = 'location'
        fields = [
            'id', 'name', 'place_type', 'place_type_display',
            'address'
        ]


class PropertyMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyMedia
        fields = '__all__'


class PropertyAmenitySerializer(serializers.ModelSerializer):
    amenity_name = serializers.CharField(
        source='amenity.name',
        read_only=True
    )
    amenity_description = serializers.CharField(
        source='amenity.description',
        read_only=True
    )
    amenity_icon = serializers.CharField(
        source='amenity.icon',
        read_only=True
    )
    amenity_id = serializers.PrimaryKeyRelatedField(
        queryset=Amenity.objects.all(),
        source='amenity',
        write_only=True
    )

    class Meta:
        model = PropertyAmenity
        fields = [
            'id', 'property', 'amenity', 'amenity_id',
            'amenity_name', 'amenity_description', 'amenity_icon'
        ]


class PropertyNearByPlacesSerializer(serializers.ModelSerializer):
    place = NearByPlacesSerializer(read_only=True)
    place_id = serializers.PrimaryKeyRelatedField(
        queryset=NearByPlaces.objects.all(),
        source='place',
        write_only=True
    )

    class Meta:
        model = PropertyNearByPlaces
        fields = [
            'id', 'property', 'place', 'place_id',
            'distance', 'walking_time'
        ]


class PropertiesSerializer(GeoFeatureModelSerializer):
    broker_name = serializers.SerializerMethodField()
    broker_email = serializers.SerializerMethodField()
    property_type_display = serializers.CharField(
        source='get_property_type_display',
        read_only=True
    )

    nearby_places = PropertyNearByPlacesSerializer(
        many=True,
        read_only=True
    )

    distance_to_university = serializers.SerializerMethodField()

    amenities = PropertyAmenitySerializer(
        many=True,
        read_only=True
    )
    amenity_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Amenity.objects.all(),
        write_only=True,
        source='amenities'
    )

    images = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()

    class Meta:
        model = Properties
        geo_field = 'location'
        fields = [
            'id', 'title', 'description', 'broker',
            'broker_name', 'broker_email', 'property_type',
            'property_type_display', 'price', 'bedrooms',
            'toilets', 'address', 'available_from',
            'lease_duration', 'is_furnished', 'is_available',
            'safety_score', 'transportation_score',
            'amenities_score', 'overall_score',
            # geometry field handled by GeoFeatureModelSerializer
            'nearby_places', 'distance_to_university',
            'amenities', 'amenity_ids', 'images', 'videos',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'broker_name', 'broker_email',
            'property_type_display', 'geometry',
            'nearby_places', 'distance_to_university',
            'amenities', 'images', 'videos',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'broker': {'write_only': True},
        }

    def get_broker_name(self, obj):
        return f"{obj.broker.first_name} {obj.broker.last_name}"

    def get_broker_email(self, obj):
        return obj.broker.email

    def get_images(self, obj):
        imgs = obj.media.filter(media_type='image')
        return [
            self.context['request'].build_absolute_uri(img.file.url)
            for img in imgs
        ]

    def get_videos(self, obj):
        vids = obj.media.filter(media_type='video')
        return [
            self.context['request'].build_absolute_uri(vid.file.url)
            for vid in vids
        ]

    def get_distance_to_university(self, obj):
        req = self.context.get('request', None)
        if not (req and req.user.is_authenticated and getattr(req.user, 'roles', None) == 'student'):
            return None

        uni = getattr(req.user.student_profile, 'university', None)
        if not uni:
            return None

        dist_obj = Properties.objects.filter(id=obj.id).annotate(
            dist=Distance('location', uni.location)
        ).values('dist').first()

        if dist_obj and dist_obj['dist'] is not None:
            return round(dist_obj['dist'].m / 1000, 2)
        return None

    def create(self, validated_data):
        amenity_list = validated_data.pop('amenities', [])
        location = validated_data.pop('location')
        prop = Properties.objects.create(location=location, **validated_data)

        for amen in amenity_list:
            PropertyAmenity.objects.create(property=prop, amenity=amen)
        return prop

    def update(self, instance, validated_data):
        amenity_list = validated_data.pop('amenities', None)
        if 'location' in validated_data:
            instance.location = validated_data.pop('location')

        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()

        if amenity_list is not None:
            instance.amenities.clear()
            for amen in amenity_list:
                PropertyAmenity.objects.create(property=instance, amenity=amen)

        return instance
