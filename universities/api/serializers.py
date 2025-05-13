from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers

class UniversitySerializer(GeoFeatureModelSerializer):
    class Meta:
        model = 'universities.University'
        geo_field = 'location'
        fields = ['id', 'name', 'logo', 'address', 'website','created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class CampusSerializer(GeoFeatureModelSerializer):
    university = serializers.PrimaryKeyRelatedField(
        queryset='universities.University.objects.all()',
    )
    class Meta:
        model = 'universities.Campus'
        geo_field = 'location'
        fields = ['id', 'name', 'university', 'address', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']