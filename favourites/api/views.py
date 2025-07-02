from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from favourites.models import Favourites
from favourites.api.serializers import FavouritesSerializer
from properties.models import Properties
from properties.api.serializers import PropertiesSerializer
from users.models import User  
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

class FavouritesViewSet(viewsets.ModelViewSet):
    queryset = Favourites.objects.all()
    serializer_class = FavouritesSerializer
    
    @extend_schema(
        description="Get all favorites for a specific user",
        parameters=[
            OpenApiParameter(
                name='user_id', 
                type=OpenApiTypes.INT, 
                location='query',
                required=True,
                description='ID of the user to fetch favorites for'
            )
        ],
        responses={200: FavouritesSerializer(many=True)}
    )
    def list(self, request):
        """Override the default list method to filter by user_id"""
        user_id = request.query_params.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id query parameter is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        favourites = Favourites.objects.filter(user=user)
        serializer = self.get_serializer(favourites, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        description="Add a property to user's favorites",
        request=FavouritesSerializer,
        responses={201: FavouritesSerializer},
        examples=[
            OpenApiExample(
                'Add Favorite',
                value={'user_id': 1, 'property_id': 1}
            )
        ]
    )
    @action(detail=False, methods=['post'], url_path='add-favourite')
    def add_favourite(self, request):
        user_id = request.data.get('user_id')
        property_id = request.data.get('property_id')
        
        try:
            user = User.objects.get(pk=user_id)
            property = Properties.objects.get(pk=property_id)
        except (User.DoesNotExist, Properties.DoesNotExist):
            return Response({'error': 'User or Property not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if Favourites.objects.filter(user=user, property=property).exists():
            return Response({'error': 'Property already in favorites'}, status=status.HTTP_400_BAD_REQUEST)
        
        favourite = Favourites.objects.create(user=user, property=property)
        serializer = self.get_serializer(favourite)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        description="Remove a property from user's favorites",
        parameters=[
            OpenApiParameter(name='user_id', type=OpenApiTypes.INT, location='query'),
            OpenApiParameter(name='property_id', type=OpenApiTypes.INT, location='query')
        ],
        responses={204: None}
    )
    @action(detail=False, methods=['delete'], url_path='remove-favourite')
    def remove_favourite(self, request):
        user_id = request.query_params.get('user_id')
        property_id = request.query_params.get('property_id')
        
        try:
            user = User.objects.get(pk=user_id)
            property = Properties.objects.get(pk=property_id)
        except (User.DoesNotExist, Properties.DoesNotExist):
            return Response({'error': 'User or Property not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            favourite = Favourites.objects.get(user=user, property=property)
            favourite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Favourites.DoesNotExist:
            return Response({'error': 'Favorite does not exist'}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        description="Get top 3 most favorited properties across all users",
        responses={200: PropertiesSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='top-properties')
    def top_favorited_properties(self, request):
        top_property_ids = (
            Favourites.objects.values('property')
            .annotate(count=Count('property'))
            .order_by('-count')[:3]
        )
        property_ids = [item['property'] for item in top_property_ids]
        properties = Properties.objects.filter(id__in=property_ids)
        serializer = PropertiesSerializer(properties, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)