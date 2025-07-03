from rest_framework import serializers
from reviews.models import PropertyReview
from drf_spectacular.utils import extend_schema_field
from typing import Optional

class PropertyReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyReview
        fields = ['id', 'property', 'reviewer', 'reviewer_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['reviewer', 'created_at']
        # Add ref_name to avoid conflicts with other PropertyReviewSerializer classes
        ref_name = 'ReviewsPropertyReview'
    
    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_reviewer_name(self, obj) -> Optional[str]:
        """Get the reviewer's full name"""
        if obj.reviewer:
            return f"{obj.reviewer.first_name} {obj.reviewer.last_name}".strip()
        return None