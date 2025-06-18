from rest_framework import viewsets, permissions
from rest_framework.exceptions import ValidationError
from reviews.models import PropertyReview
from .serializers import PropertyReviewSerializer

class PropertyReviewViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = PropertyReview.objects.all()
        property_id = self.request.query_params.get('property', None)
        if property_id:
            queryset = queryset.filter(property_id=property_id)
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        # Check if user has already reviewed this property
        property_id = self.request.data.get('property')
        existing_review = PropertyReview.objects.filter(
            reviewer=self.request.user,
            property_id=property_id
        ).exists()
        
        if existing_review:
            raise ValidationError("You have already reviewed this property")
        
        serializer.save(reviewer=self.request.user)
