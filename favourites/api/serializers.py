from rest_framework import serializers
from favourites.models import Favourites
from users.api.serializers import UserSerializer  
from properties.api.serializers import PropertiesSerializer 

class FavouritesSerializer(serializers.ModelSerializer):
    # Nested serializers for read operations
    user = UserSerializer(read_only=True)
    property = PropertiesSerializer(read_only=True)
    # Primary key fields for write operations
    user_id = serializers.PrimaryKeyRelatedField(
        source='user',
        queryset=user.objects.all(),
        write_only=True
    )
    property_id = serializers.PrimaryKeyRelatedField(
        source='property',
        queryset=property.objects.all(),
        write_only=True
    )

    class Meta:
        model = Favourites
        fields = [
            'id',
            'user', 'user_id',
            'property', 'property_id',
            'added_at'
        ]
        read_only_fields = ['id', 'added_at']
        extra_kwargs = {
            'user': {'read_only': True},
            'property': {'read_only': True},
        }

    def validate(self, data):
        """Check for duplicate favorites"""
        user = data.get('user')
        property = data.get('property')
        
        if Favourites.objects.filter(user=user, property=property).exists():
            raise serializers.ValidationError(
                "This property is already in your favorites."
            )
        return data