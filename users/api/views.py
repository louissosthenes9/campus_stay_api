from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, StudentProfileSerializer, BrokerProfileSerializer
from users.models import StudentProfile, BrokerProfile
import logging
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from google.oauth2 import id_token
from google.auth.transport import requests

# Configure logging
logger = logging.getLogger(__name__)

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'login', 'google_login']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        # Start a transaction so we can rollback if anything fails
        from django.db import transaction
        
        try:
            with transaction.atomic():
                # Validate and create the user
                user_serializer = self.get_serializer(data=request.data)
                if not user_serializer.is_valid():
                    logger.error(f"User validation failed: {user_serializer.errors}")
                    return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                # Save the user - note: removed email verification
                user = user_serializer.save()
                logger.info(f"User created successfully: {user.username} ({user.pk})")
                
                # Handle profile creation based on user type
                if user.user_type == 'student':
                    self._create_student_profile(request, user)
                elif user.user_type == 'broker':
                    self._create_broker_profile(request, user)
                else:
                    logger.warning(f"Unknown user_type: {user.user_type}")
                
                # Generate tokens
                refresh = RefreshToken.for_user(user)
                
                response_data = {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': user_serializer.data
                }
                
                return Response(response_data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"Unexpected error during user creation: {str(e)}")
            return Response(
                {'detail': 'An unexpected error occurred during registration.'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _create_student_profile(self, request, user):
        """Create a student profile for the user."""
        student_data = request.data.get('student_profile', {})
        logger.debug(f"Creating student profile with data: {student_data}")
        
        # Check if university is provided as ID or name
        if 'university_name' in student_data and 'university' not in student_data:
            from users.models import University  # Import here to avoid circular imports
            try:
                university = University.objects.get(name=student_data['university_name'])
                student_data['university'] = university.id
            except University.DoesNotExist:
                logger.warning(f"University with name '{student_data['university_name']}' not found")
        
        student_serializer = StudentProfileSerializer(data=student_data)
        if student_serializer.is_valid():
            student_profile = student_serializer.save(user=user)
            logger.info(f"Created student profile for user {user.pk}: {student_profile.pk}")
        else:
            logger.error(f"Student profile validation failed: {student_serializer.errors}")
            raise ValueError(f"Invalid student profile data: {student_serializer.errors}")
    
    def _create_broker_profile(self, request, user):
        """Create a broker profile for the user."""
        broker_data = request.data.get('broker_profile', {})
        logger.debug(f"Creating broker profile with data: {broker_data}")
        
        broker_serializer = BrokerProfileSerializer(data=broker_data)
        if broker_serializer.is_valid():
            broker_profile = broker_serializer.save(user=user)
            logger.info(f"Created broker profile for user {user.pk}: {broker_profile.pk}")
        else:
            logger.error(f"Broker profile validation failed: {broker_serializer.errors}")
            raise ValueError(f"Invalid broker profile data: {broker_serializer.errors}")
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Return the current authenticated user's details."""
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
            
        serializer = self.get_serializer(request.user)
        
        # Include profile data if it exists
        data = serializer.data
        
        if request.user.user_type == 'student':
            try:
                profile = StudentProfile.objects.get(user=request.user)
                data['student_profile'] = StudentProfileSerializer(profile).data
            except StudentProfile.DoesNotExist:
                data['student_profile'] = None
        
        elif request.user.user_type == 'broker':
            try:
                profile = BrokerProfile.objects.get(user=request.user)
                data['broker_profile'] = BrokerProfileSerializer(profile).data
            except BrokerProfile.DoesNotExist:
                data['broker_profile'] = None
                
        return Response(data)
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """Traditional username/password login"""
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'detail': 'Both username and password are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response(
                {'detail': 'Invalid credentials'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        refresh = RefreshToken.for_user(user)
        
        serializer = self.get_serializer(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def google_login(self, request):
        """Login or register with Google OAuth"""
        token = request.data.get('token')
        
        if not token:
            return Response(
                {'detail': 'Google token is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Verify the token with Google
            idinfo = id_token.verify_oauth2_token(
                token, 
                requests.Request(), 
                settings.GOOGLE_OAUTH2_CLIENT_ID
            )
            
            # Extract Google user info
            google_user_id = idinfo['sub']
            email = idinfo.get('email')
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            
            # Check if user exists
            try:
                user = User.objects.get(email=email)
                logger.info(f"Google login: Existing user found for email {email}")
                
                # Update user info if needed
                if not user.google_id:
                    user.google_id = google_user_id
                    user.save()
                    
            except User.DoesNotExist:
                # Create a new user
                username = email.split('@')[0]
                base_username = username
                counter = 1
                
                # Ensure username is unique
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    google_id=google_user_id,
                    # Set a random password since user will login via Google
                    password=User.objects.make_random_password()
                )
                logger.info(f"Google login: Created new user for email {email}")
                
                # Set default user type - adjust as needed
                user.user_type = 'student'  # or get from request
                user.save()
                
                # You might want to create default profiles here
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            serializer = self.get_serializer(user)
            
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': serializer.data,
                'is_new_user': not user.last_login,  # Check if new user
            })
            
        except ValueError as e:
            # Invalid token
            logger.error(f"Google login failed: {str(e)}")
            return Response(
                {'detail': 'Invalid Google token'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            logger.error(f"Unexpected error during Google login: {str(e)}")
            return Response(
                {'detail': 'Authentication failed'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )