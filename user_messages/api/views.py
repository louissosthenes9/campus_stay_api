from rest_framework import status, viewsets, mixins, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view
from drf_spectacular.types import OpenApiTypes

from .models import Enquiry, EnquiryMessage, EnquiryStatus
from .serializers import EnquirySerializer, CreateEnquirySerializer, EnquiryMessageSerializer

class IsEnquiryParticipant(permissions.BasePermission):
    """
    Custom permission to only allow participants of an enquiry to view it.
    """
    def has_object_permission(self, request, view, obj):
        # Allow if the request user is the student who made the enquiry
        # or the property owner
        is_student = obj.student.user == request.user
        is_property_owner = obj.property.user == request.user
        return is_student or is_property_owner

@extend_schema_view(
    list=extend_schema(
        description="List all enquiries for the authenticated user",
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by status (pending, in_progress, resolved, cancelled)'
            ),
            OpenApiParameter(
                name='is_active',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter by active status'
            ),
            OpenApiParameter(
                name='property_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by property ID'
            ),
        ]
    ),
    create=extend_schema(description="Create a new enquiry about a property"),
    retrieve=extend_schema(description="Retrieve details of a specific enquiry"),
    update=extend_schema(description="Update an enquiry status"),
    partial_update=extend_schema(description="Partially update an enquiry"),
    destroy=extend_schema(description="Cancel an enquiry (students only)"),
)
class EnquiryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing property enquiries.
    Students can create and view their own enquiries.
    Property owners can view and update enquiries for their properties.
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Get all enquiries where the user is the student or the property owner
        queryset = Enquiry.objects.filter(
            Q(student__user=self.request.user) | Q(property__user=self.request.user)
        ).select_related('property', 'student__user', 'property__user').prefetch_related('messages')
        
        # Filter by status if provided
        status_param = self.request.query_params.get('status')
        if status_param in dict(EnquiryStatus.choices):
            queryset = queryset.filter(status=status_param)
            
        # Filter by property_id if provided
        property_id = self.request.query_params.get('property_id')
        if property_id:
            queryset = queryset.filter(property_id=property_id)
            
        # Filter by is_active if provided
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
        return queryset.order_by('-updated_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreateEnquirySerializer
        return EnquirySerializer
    
    def perform_create(self, serializer):
        # The student is set in the serializer
        serializer.save()
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.student.user != request.user:
            return Response(
                {"detail": "You can only cancel your own enquiries."},
                status=status.HTTP_403_FORBIDDEN
            )
        instance.is_active = False
        instance.status = EnquiryStatus.CANCELLED
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark all messages in an enquiry as read."""
        enquiry = self.get_object()
        # Only the property owner can mark messages as read
        if enquiry.property.user != request.user:
            return Response(
                {"detail": "Only the property owner can mark messages as read."},
                status=status.HTTP_403_FORBIDDEN
            )
        enquiry.messages.filter(is_read=False).update(is_read=True)
        return Response({"status": "Messages marked as read"})

@extend_schema_view(
    create=extend_schema(description="Send a new message in an enquiry"),
    list=extend_schema(description="List all messages in an enquiry"),
)
class EnquiryMessageViewSet(mixins.CreateModelMixin, 
                          mixins.ListModelMixin,
                          viewsets.GenericViewSet):
    """
    ViewSet for managing messages within an enquiry.
    """
    serializer_class = EnquiryMessageSerializer
    permission_classes = [IsAuthenticated, IsEnquiryParticipant]
    
    def get_queryset(self):
        enquiry_id = self.kwargs.get('enquiry_id')
        return EnquiryMessage.objects.filter(
            enquiry_id=enquiry_id
        ).select_related('sender').order_by('created_at')
    
    def perform_create(self, serializer):
        enquiry = Enquiry.objects.get(id=self.kwargs.get('enquiry_id'))
        serializer.save(
            enquiry=enquiry,
            sender=self.request.user
        )
        
        # Mark the enquiry as in progress if it was pending
        if enquiry.status == EnquiryStatus.PENDING:
            enquiry.status = EnquiryStatus.IN_PROGRESS
            enquiry.save()
            
        # Mark other messages as read if the sender is the property owner
        if enquiry.property.user == self.request.user:
            enquiry.messages.filter(is_read=False).update(is_read=True)
