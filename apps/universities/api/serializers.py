from rest_framework import serializers
from apps.universities.models import University, Campus

class CampusSerializer(serializers.ModelSerializer):
    latitude = serializers.FloatField(source='location.y', read_only=True)
    longitude = serializers.FloatField(source='location.x', read_only=True)
    
    class Meta:
        model = Campus
        fields = ['id', 'name', 'address', 'latitude', 'longitude', 'university']

class UniversitySerializer(serializers.ModelSerializer):
    campuses = CampusSerializer(many=True, read_only=True)
    latitude = serializers.FloatField(source='location.y', read_only=True)
    longitude = serializers.FloatField(source='location.x', read_only=True)
    
    class Meta:
        model = University
        fields = ['id', 'name', 'address', 'website', 'latitude', 'longitude', 'campuses']