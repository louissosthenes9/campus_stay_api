from rest_framework import viewsets, filters, permissions, status
from rest_framework.response import Response
from universities.models import University, Campus
from universities.api.serializers import UniversitySerializer, CampusSerializer

class UniversitiesViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows universities to be viewed or edited.
    """
    queryset = University.objects.all()
    serializer_class = UniversitySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'address']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        """
        List all universities (authenticated users only).
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
        campus_serializer = CampusSerializer(campuses, many=True)
        data['campuses'] = campus_serializer.data['features'] if campus_serializer.data['features'] else []
        
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
