from rest_framework import serializers
from django.contrib.gis.db.models.functions import Distance
from django.db.models import F
from properties.models import Properties, PropertyAmenity,PropertyMedia, PropertyNearByPlaces,NearByPlaces,Amenity
from django.contrib.gis.geos import Point

class NearByPlacesSerializer(serializers.ModelSerializer):
    place_type_display = serializers.CharField(source='get_place_type_display',read_only=True)
    class Meta:
        model = NearByPlaces
        fields = ['id','name','place_type','place_type_display','location','address','created_at','updated_at']

class PropertyMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyMedia
        fields = '__all__'
class PropertyAmenitySerializer(serializers.ModelSerializer):
    amenity_name = serializers.CharField(source='amenity.name', read_only=True)
    amenity_description = serializers.CharField(source='amenity.description', read_only=True)
    amenity_icon = serializers.CharField(source='amenity.icon', read_only=True)
    amenity_id = serializers.PrimaryKeyRelatedField(
        queryset=Amenity.objects.all(),
        source='amenity',
        write_only=True
    )
    class Meta:
        model = PropertyAmenity
        fields = ['id', 'property', 'amenity', 'amenity_id', 'amenity_name', 'amenity_description', 'amenity_icon']

class PropertyNearByPlacesSerializer(serializers.ModelSerializer):
    place = NearByPlacesSerializer(read_only=True)
    place_id = serializers.PrimaryKeyRelatedField(
        queryset=NearByPlaces.objects.all(),
        source='place',
        write_only=True
    )
    class Meta:
        model = PropertyNearByPlaces
        fields = ['id','property','place','place_id','distance','walking_time']


class PropertiesSerializer(serializers.ModelSerializer):
    broker_name = serializers.SerializerMethodField()
    broker_email = serializers.SerializerMethodField()
    property_type_display = serializers.CharField(source='get_property_type_display', read_only=True)
    nearby_places = PropertyNearByPlacesSerializer(many=True, read_only=True)
    latitude = serializers.FloatField(write_only=True, required=True)
    longitude = serializers.FloatField(write_only=True, required=True)
    distance_to_university = serializers.SerializerMethodField()
    amenities = PropertyAmenitySerializer(many=True, read_only=True)
    amenity_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Amenity.objects.all(),
        write_only=True,
        source='amenities'
    )

    images = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()

    def get_broker_name(self, obj):
        return f"{obj.broker.first_name} {obj.broker.last_name}"

    def get_broker_email(self, obj):
        return obj.broker.email

    def get_images(self, obj):
        images = obj.media.filter(media_type='image')
        return [self.context['request'].build_absolute_uri(image.file.url) for image in images]

    def get_videos(self, obj):
        videos = obj.media.filter(media_type='video')
        return [self.context['request'].build_absolute_uri(video.file.url) for video in videos]

    def get_distance_to_university(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user') or not request.user.is_authenticated:
            return None

        if request.user.roles != 'student':
            return None

        try:
            university = request.user.student_profile.university

            # Calculate distance in meters
            distance = Properties.objects.filter(id=obj.id).annotate(
                dist=Distance('location', university.location)
            ).values('dist').first()

            if distance:
                # Convert to kilometers
                return round(distance['dist'].m / 1000, 2)
            return None
        except Exception as e:
            return None

    def create(self, validated_data):
        latitude = validated_data.pop('latitude')
        longitude = validated_data.pop('longitude')
        amenities_data = validated_data.pop('amenities', [])

        property_instance = Properties.objects.create(
            location=Point(longitude, latitude, srid=4326),
            **validated_data
        )

        for amenity in amenities_data:
            PropertyAmenity.objects.create(property=property_instance, amenity=amenity)

        return property_instance

    def update(self, instance, validated_data):
        latitude = validated_data.pop('latitude', None)
        longitude = validated_data.pop('longitude', None)
        amenities_data = validated_data.pop('amenities', None)

        if latitude and longitude:
            instance.location = Point(longitude, latitude, srid=4326)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if amenities_data is not None:
            instance.amenities.all().delete()
            for amenity in amenities_data:
                PropertyAmenity.objects.create(property=instance, amenity=amenity)

        return instance

    class Meta:
        model = Properties
        fields = [
            'id',
            'title',
            'description',
            'broker',
            'broker_name',
            'broker_email',
            'property_type',
            'property_type_display',
            'price',
            'bedrooms',
            'toilets',
            'address',
            'location',
            'latitude',
            'longitude',
            'available_from',
            'lease_duration',
            'is_furnished',
            'is_available',
            'safety_score',
            'transportation_score',
            'amenities_score',
            'overall_score',
            'created_at',
            'updated_at',
            'nearby_places',
            'distance_to_university',
            'amenities',
            'amenity_ids',
            'images',  
            'videos',  
        ]
        read_only_fields = ['id', 'broker_name', 'broker_email', 'property_type_display', 'location', 'created_at', 'updated_at', 'nearby_places', 'distance_to_university', 'amenities', 'images', 'videos']
        extra_kwargs = {
            'broker': {'write_only': True},
        }