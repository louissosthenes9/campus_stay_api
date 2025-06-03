from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers
from universities.models import University, Campus  # Import the actual model classes


class UniversitySerializer(GeoFeatureModelSerializer):
    class Meta:
        model = University  # Use the actual class, not a string
        geo_field = 'location'
        fields = ['id', 'name', 'logo', 'address', 'website', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class CampusSerializer(GeoFeatureModelSerializer):
    university = serializers.PrimaryKeyRelatedField(
        queryset=University.objects.all(),  # Use the actual queryset, not a string
    )
    university_name = serializers.CharField(source='university.name', read_only=True)
    
    class Meta:
        model = Campus  # Use the actual class, not a string
        geo_field = 'location'
        fields = ['id', 'name', 'university', 'university_name', 'address', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']