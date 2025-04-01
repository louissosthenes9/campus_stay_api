from rest_framework import serializers
from favourites.models import Favorite
from properties.api.serializers import PropertySerializer

class FavoriteSerializer(serializers.ModelSerializer):
    property_details = PropertySerializer(source='property', read_only=True)
    
    class Meta:
        model = Favorite
        fields = ['id', 'property', 'property_details', 'added_at']
        read_only_fields = ['added_at']