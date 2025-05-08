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
from django.db import transaction

# Configure logging
logger = logging.getLogger(__name__)

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().select_related('studentprofile', 'brokerprofile')
    serializer_class = UserSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'login', 'google_login']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        # Validate request data before starting any database operations
        roles = request.data.get('roles')
        if not roles or roles not in ['student', 'broker', 'admin']:
            return Response(
                {'roles': 'A valid user type (student, broker, admin) is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate user data first to avoid unnecessary processing
        user_serializer = self.get_serializer(data=request.data)
        if not user_serializer.is_valid():
            return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Pre-validate profile data if applicable
        if roles == 'student':
            student_data = request.data.get('student_profile', {})
            if not student_data.get('university') and not student_data.get('university_name'):
                return Response(
                    {'student_profile': 'University is required for student profiles'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            if not student_data.get('course'):
                return Response(
                    {'student_profile': 'Course information is required for student profiles'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Handle university lookup outside transaction if needed
            if 'university_name' in student_data and 'university' not in student_data:
                from universities.models import University
                try:
                    university = University.objects.get(name=student_data['university_name'])
                    student_data['university'] = university.id
                except University.DoesNotExist:
                    return Response(
                        {'student_profile': f"University with name '{student_data['university_name']}' not found"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                    
            # Pre-validate student profile
            student_serializer = StudentProfileSerializer(data=student_data)
            if not student_serializer.is_valid():
                return Response(
                    {'student_profile': student_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        elif roles == 'broker':
            broker_data = request.data.get('broker_profile', {})
            broker_serializer = BrokerProfileSerializer(data=broker_data)
            if not broker_serializer.is_valid():
                return Response(
                    {'broker_profile': broker_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            # Now perform the actual database operations in a transaction
            with transaction.atomic():
                # Create user
                user = user_serializer.save()
                
                # Create profile in the same transaction but with minimal operations
                if user.roles == 'student':
                    student_data = request.data.get('student_profile', {})
                    # We already validated the serializer above, so just save
                    student_serializer = StudentProfileSerializer(data=student_data)
                    student_serializer.is_valid()  # This will pass since we validated earlier
                    student_serializer.save(user=user)
                    
                elif user.roles == 'broker':
                    broker_data = request.data.get('broker_profile', {})
                    broker_serializer = BrokerProfileSerializer(data=broker_data)
                    broker_serializer.is_valid()  # This will pass since we validated earlier
                    broker_serializer.save(user=user)
            
            # Generate tokens outside the transaction
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
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Return the current authenticated user's details."""
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
            
        serializer = self.get_serializer(request.user)
        data = serializer.data
        
        # Use the prefetched relations from our queryset
        if request.user.roles == 'student':
            try:
                # Access the profile directly through the attribute
                profile = getattr(request.user, 'studentprofile', None)
                if profile:
                    data['student_profile'] = StudentProfileSerializer(profile).data
                else:
                    data['student_profile'] = None
            except StudentProfile.DoesNotExist:
                data['student_profile'] = None
        
        elif request.user.roles == 'broker':
            try:
                profile = getattr(request.user, 'brokerprofile', None)
                if profile:
                    data['broker_profile'] = BrokerProfileSerializer(profile).data
                else:
                    data['broker_profile'] = None
            except BrokerProfile.DoesNotExist:
                data['broker_profile'] = None
                
        return Response(data)
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """Traditional username/email and password login"""
        username_or_email = request.data.get('username')
        password = request.data.get('password')
        
        if not username_or_email or not password:
            return Response(
                {'detail': 'Both username/email and password are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Try to authenticate with the given credentials as username
        user = authenticate(username=username_or_email, password=password)
        
        # If authentication with username fails, try with email
        if user is None:
            try:
                # Find the user with the given email
                user_obj = User.objects.get(email=username_or_email)
                # Try to authenticate with the found username
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        
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
        token = request.data.get('id_token')
        
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
            
            # Attempt to find user in a single query with profiles
            user = None
            try:
                user = User.objects.select_related(
                    'studentprofile', 'brokerprofile'
                ).get(email=email)
                
                # Update user info if needed - only if google_id is missing
                if not user.google_id:
                    user.google_id = google_user_id
                    user.save(update_fields=['google_id'])
                
                # Check if user has completed onboarding
                if not user.roles:
                    return Response({
                        'status': 'onboarding_required',
                        'email': email,
                        'first_name': first_name,
                        'last_name': last_name,
                        'google_id': google_user_id,
                        'temp_token': self._generate_onboarding_token(email, google_user_id)
                    }, status=status.HTTP_200_OK)
                
                # Check if profile exists for the user type
                if user.roles == 'student':
                    has_profile = hasattr(user, 'studentprofile')
                    if not has_profile:
                        return Response({
                            'status': 'profile_required',
                            'roles': user.roles,
                            'email': email,
                            'temp_token': self._generate_onboarding_token(email, google_user_id)
                        }, status=status.HTTP_200_OK)
                elif user.roles == 'broker':
                    has_profile = hasattr(user, 'brokerprofile')
                    if not has_profile:
                        return Response({
                            'status': 'profile_required',
                            'roles': user.roles,
                            'email': email,
                            'temp_token': self._generate_onboarding_token(email, google_user_id)
                        }, status=status.HTTP_200_OK)
                    
            except User.DoesNotExist:
                # This is a new user, we need them to complete onboarding
                return Response({
                    'status': 'onboarding_required',
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'google_id': google_user_id,
                    'temp_token': self._generate_onboarding_token(email, google_user_id)
                }, status=status.HTTP_200_OK)
            
            # User exists and has completed onboarding - generate tokens
            refresh = RefreshToken.for_user(user)
            serializer = self.get_serializer(user)
            
            return Response({
                'status': 'success',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': serializer.data
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

    # Cache the SECRET_KEY to avoid repeated lookups
    _SECRET_KEY = None
    
    def _get_secret_key(self):
        if self._SECRET_KEY is None:
            self.__class__._SECRET_KEY = settings.SECRET_KEY
        return self._SECRET_KEY
    
    def _generate_onboarding_token(self, email, google_id):
        """Generate a temporary token for completing the onboarding process."""
        import jwt
        import time
        
        payload = {
            'email': email,
            'google_id': google_id,
            'exp': int(time.time()) + 3600  # 1 hour expiry
        }
        
        token = jwt.encode(payload, self._get_secret_key(), algorithm='HS256')
        return token
        
    @action(detail=False, methods=['post'])
    def complete_google_onboarding(self, request):
        """Complete the registration process after Google login."""
        temp_token = request.data.get('temp_token')
        roles = request.data.get('roles')
        
        if not temp_token or not roles:
            return Response(
                {'detail': 'Missing required fields'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if roles not in ['student', 'broker']:
            return Response(
                {'detail': 'Invalid user type'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Verify the temporary token
            import jwt
            payload = jwt.decode(temp_token, self._get_secret_key(), algorithms=['HS256'])
            email = payload.get('email')
            google_id = payload.get('google_id')
            
            # Pre-validate profile data
            if roles == 'student':
                profile_data = request.data.get('student_profile', {})
                if not profile_data or 'university' not in profile_data:
                    return Response(
                        {'detail': 'University selection required for students'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                student_serializer = StudentProfileSerializer(data=profile_data)
                if not student_serializer.is_valid():
                    return Response(student_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            elif roles == 'broker':
                profile_data = request.data.get('broker_profile', {})
                broker_serializer = BrokerProfileSerializer(data=profile_data)
                if not broker_serializer.is_valid():
                    return Response(broker_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                # Check if user exists
                user = None
                created = False
                try:
                    user = User.objects.select_for_update().get(email=email)
                    # Update user type if needed
                    if not user.roles:
                        user.roles = roles
                        user.save(update_fields=['roles'])
                except User.DoesNotExist:
                    # Create new user
                    username = email.split('@')[0]
                    base_username = username
                    counter = 1
                    
                    # Ensure username is unique - cached query approach
                    existing_usernames = list(User.objects.filter(
                        username__startswith=base_username
                    ).values_list('username', flat=True))
                    
                    while username in existing_usernames:
                        username = f"{base_username}{counter}"
                        counter += 1
                    
                    # Set a random password for security
                    password = User.objects.make_random_password()
                    
                    # Set first_name and last_name from request or defaults
                    first_name = request.data.get('first_name', '')
                    last_name = request.data.get('last_name', '')
                    
                    # Create the user in one operation
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        google_id=google_id,
                        roles=roles,
                        password=password,
                        first_name=first_name,
                        last_name=last_name
                    )
                    created = True
                
                # Handle profile creation based on user type
                if roles == 'student':
                    profile_data = request.data.get('student_profile', {})
                    
                    if created:
                        # New user - direct create
                        StudentProfile.objects.create(user=user, **profile_data)
                    else:
                        # Existing user - update or create
                        StudentProfile.objects.update_or_create(
                            user=user,
                            defaults=profile_data
                        )
                        
                elif roles == 'broker':
                    profile_data = request.data.get('broker_profile', {})
                    
                    if created:
                        # New user - direct create
                        BrokerProfile.objects.create(user=user, **profile_data)
                    else:
                        # Existing user - update or create
                        BrokerProfile.objects.update_or_create(
                            user=user,
                            defaults=profile_data
                        )
            
            # Generate tokens for authentication - outside transaction
            refresh = RefreshToken.for_user(user)
            serializer = self.get_serializer(user)
            
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': serializer.data
            }, status=status.HTTP_200_OK)
            
        except jwt.ExpiredSignatureError:
            return Response(
                {'detail': 'Onboarding session expired'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        except jwt.DecodeError:
            return Response(
                {'detail': 'Invalid onboarding token'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            logger.error(f"Error completing Google onboarding: {str(e)}")
            return Response(
                {'detail': 'Failed to complete registration'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )