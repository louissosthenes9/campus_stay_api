from rest_framework import viewsets, permissions, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from rest_framework.decorators import action
from rest_framework.response import Response
from .serializers import PropertiesSerializer
from properties.models import Properties
from universities.models import University
from django.db import transaction

# class IsBrokerOrAdmin(permissions.BasePermission):
#     def has_permission(self, request, view):
#         return request.user.is_authenticated and (
#             request.user.roles in ['broker', 'admin'] or 
#             request.user.is_staff
#         )

class PropertiesViewSet(viewsets.ModelViewSet):
    queryset = Properties.objects.all()
    serializer_class = PropertiesSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['property_type', 'broker', 'price', 'bedrooms', 'toilets', 'is_furnished']
    search_fields = ['title', 'description', 'address']
    ordering_fields = ['price', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = Properties.objects.filter(is_available=True)
        university_id = self.request.query_params.get('university_id')
        distance = self.request.query_params.get('distance', 5)
        
        if university_id:
            try:
                university = University.objects.get(id=university_id)
                queryset = queryset.annotate(
                    distance=Distance('location', university.location)
                ).filter(distance__lte=D(km=float(distance))).order_by('distance')
            except University.DoesNotExist:
                return Properties.objects.none()
        return queryset

    # def get_permissions(self):
    #     if self.action in ['create', 'update', 'partial_update', 'destroy']:
    #         self.permission_classes = [IsBrokerOrAdmin]
    #     return super().get_permissions()

    def perform_create(self, serializer):
        with transaction.atomic():
            if self.request.user.roles == 'broker':
                serializer.save(broker=self.request.user)
            else:
                serializer.save()

    @action(detail=False, methods=['get'], url_path='near-university')
    def near_university(self, request):
        if request.user.roles != 'student':
            return Response({"error": "This endpoint is only for students"}, 
                            status=status.HTTP_403_FORBIDDEN)
        if not hasattr(request.user, 'student_profile') or not request.user.student_profile.university_id:
            return Response({"error": "Student profile or university not set"}, 
                            status=status.HTTP_400_BAD_REQUEST)
        university_id = request.user.student_profile.university_id
        distance = request.query_params.get('distance', 5)
        try:
            university = University.objects.get(id=university_id)
            properties = Properties.objects.filter(is_available=True).annotate(
                distance=Distance('location', university.location)
            ).filter(distance__lte=D(km=float(distance))).order_by('distance')
            serializer = self.get_serializer(properties, many=True, context={'request': request})
            return Response(serializer.data)
        except University.DoesNotExist:
            return Response({"error": "University not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='my-properties')
    def my_properties(self, request):
        if request.user.roles != 'broker':
            return Response({"error": "This endpoint is only for brokers"}, 
                        status=status.HTTP_403_FORBIDDEN)
        properties = Properties.objects.filter(broker=request.user)
        serializer = self.get_serializer(properties, many=True, context={'request': request})
        return Response(serializer.data)