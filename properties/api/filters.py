import django_filters
from django.db import models
from django_filters import rest_framework as filters
from properties.models import Properties, Amenity

class PropertyFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name="price", lookup_expr='gte')
    max_price = filters.NumberFilter(field_name="price", lookup_expr='lte')
    property_type = filters.BaseInFilter(field_name='property_type', lookup_expr='in')
    amenities = filters.ModelMultipleChoiceFilter(
        field_name='amenities__amenity__id',
        to_field_name='id',
        queryset=Amenity.objects.all(),
        conjoined=True  # All specified amenities must match (AND condition)
    )
    
    electricity_type = filters.MultipleChoiceFilter(
        field_name='electricity_type',
        choices=Properties.ELECTRICITY_TYPE_CHOICES,
        lookup_expr='iexact',
        help_text="Filter by electricity type. Can specify multiple values."
    )
    
    class Meta:
        model = Properties
        fields = {
            'bedrooms': ['exact', 'gte', 'lte'],
            'toilets': ['exact', 'gte', 'lte'],
            'is_furnished': ['exact'],
            'is_special_needs': ['exact'],
            'is_fenced': ['exact'],
            'water_supply': ['exact'],
            'electricity_type': ['exact'],
        }
    
    def filter_queryset(self, queryset):
        # Apply the default filtering
        queryset = super().filter_queryset(queryset)
        
        # Apply custom filters
        params = self.request.query_params
        
        # Handle price range
        if 'min_price' in params or 'max_price' in params:
            price_lookup = {}
            if 'min_price' in params:
                price_lookup['price__gte'] = params['min_price']
            if 'max_price' in params:
                price_lookup['price__lte'] = params['max_price']
            queryset = queryset.filter(**price_lookup)
        
        # Handle amenities (already handled by ModelMultipleChoiceFilter)
        
        return queryset
