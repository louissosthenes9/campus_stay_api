from rest_framework import viewsets, filters, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.openapi import OpenApiTypes
from universities.models import University, Campus
from universities.api.serializers import UniversitySerializer, CampusSerializer


@extend_schema_view(
    list=extend_schema(
        description="List all universities",
        summary="Get all universities (public endpoint)"
    ),
    retrieve=extend_schema(
        description="Retrieve a single university by ID with its associated campuses",
        summary="Get university details with campuses (authenticated users only)"
    ),
    create=extend_schema(
        description="Create a new university",
        summary="Create university (admin only)"
    ),
    update=extend_schema(
        description="Update an existing university",
        summary="Update university (admin only)"
    ),
    partial_update=extend_schema(
        description="Partially update an existing university",
        summary="Partially update university (admin only)"
    ),
    destroy=extend_schema(
        description="Delete a university",
        summary="Delete university (admin only)"
    ),
)
class UniversitiesViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows universities to be viewed or edited.
    """
    queryset = University.objects.all()
    serializer_class = UniversitySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'address']

    def get_permissions(self):
        if self.action == 'list':
            # allow unauthenticated users to list
            return [permissions.AllowAny()]
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        # retrieve/detail still requires an authenticated user
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        """
        List all universities
        """
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single university by ID with its associated campuses (authenticated users only).
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        
        # Add associated campuses to the response
        campuses = instance.campuses.all()
        campus_serializer = CampusSerializer(campuses, many=True, context={'request': request})
        
        # Handle GeoFeatureModelSerializer response format
        campus_data = campus_serializer.data
        if isinstance(campus_data, dict) and 'features' in campus_data:
            data['campuses'] = campus_data['features']
        else:
            data['campuses'] = campus_data
        
        return Response(data)

    def create(self, request, *args, **kwargs):
        """
        Create a new university (admin only).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
        Update an existing university (admin only).
        """
        partial = False
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """
        Partially update an existing university (admin only).
        """
        partial = True
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a university (admin only).
        """
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(
        description="List all campuses",
        summary="Get all campuses (authenticated users only)"
    ),
    retrieve=extend_schema(
        description="Retrieve a single campus by ID",
        summary="Get campus details (authenticated users only)"
    ),
    create=extend_schema(
        description="Create a new campus",
        summary="Create campus (admin only)"
    ),
    update=extend_schema(
        description="Update an existing campus",
        summary="Update campus (admin only)"
    ),
    partial_update=extend_schema(
        description="Partially update an existing campus",
        summary="Partially update campus (admin only)"
    ),
    destroy=extend_schema(
        description="Delete a campus",
        summary="Delete campus (admin only)"
    ),
)
class CampusViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows campuses to be viewed or edited.
    """
    queryset = Campus.objects.select_related('university').all()
    serializer_class = CampusSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'address']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        """
        List all campuses (authenticated users only).
        """
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a single campus by ID (authenticated users only).
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create a new campus (admin only).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
        Update an existing campus (admin only).
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """
        Partially update an existing campus (admin only).
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a campus (admin only).
        """
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)