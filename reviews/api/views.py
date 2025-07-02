from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
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
       
    @action(detail=False, methods=['get'], url_path='user-reviews/(?P<user_id>[^/.]+)')
    def user_reviews(self, request, user_id=None):
        reviews = PropertyReview.objects.filter(reviewer__id=user_id).order_by('-created_at')
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='property-reviews/(?P<property_id>[^/.]+)')
    def property_reviews(self, request, property_id=None):
        """Get all reviews for a specific property"""
        reviews = PropertyReview.objects.filter(property_id=property_id).order_by('-created_at')
        serializer = self.get_serializer(reviews, many=True)
        return Response(serializer.data)