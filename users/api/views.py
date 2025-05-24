from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, StudentProfileSerializer
from users.models import StudentProfile
import logging
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from google.oauth2 import id_token
from google.auth.transport import requests
from django.db import transaction
from .serializers import CustomTokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

# Configure logging
logger = logging.getLogger(__name__)

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().select_related('student_profile')
    serializer_class = UserSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'login', 'google_login']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        roles = request.data.get('roles')
        if not roles or roles not in ['student', 'admin']:
            return Response(
                {'roles': 'A valid user type (student, admin) is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_serializer = self.get_serializer(data=request.data)
        if not user_serializer.is_valid():
            return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
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
                    
            student_serializer = StudentProfileSerializer(data=student_data)
            if not student_serializer.is_valid():
                return Response(
                    {'student_profile': student_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            with transaction.atomic():
                user = user_serializer.save()
                
                if user.roles == 'student':
                    student_data = request.data.get('student_profile', {})
                    student_serializer = StudentProfileSerializer(data=student_data)
                    student_serializer.is_valid()
                    student_serializer.save(user=user)
            
            refresh = CustomTokenObtainPairSerializer.get_token(user)
            
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
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
            
        serializer = self.get_serializer(request.user)
        data = serializer.data
        
        if request.user.roles == 'student':
            try:
                profile = getattr(request.user, 'student_profile', None)
                if profile:
                    data['student_profile'] = StudentProfileSerializer(profile).data
                else:
                    data['student_profile'] = None
            except StudentProfile.DoesNotExist:
                data['student_profile'] = None
        
        return Response(data)
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        username_or_email = request.data.get('username')
        password = request.data.get('password')
        
        if not username_or_email or not password:
            return Response(
                {'detail': 'Both username/email and password are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(username=username_or_email, password=password)
        
        if user is None:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        
        if user is None:
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        refresh = CustomTokenObtainPairSerializer.get_token(user)
        serializer = self.get_serializer(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def google_login(self, request):
        token = request.data.get('id_token')
        
        if not token:
            return Response({'detail': 'Google token is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            idinfo = id_token.verify_oauth2_token(
                token, requests.Request(), settings.GOOGLE_OAUTH2_CLIENT_ID
            )
            
            google_user_id = idinfo['sub']
            email = idinfo.get('email')
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            
            user = None
            try:
                user = User.objects.select_related('student_profile').get(email=email)
                
                if not user.google_id:
                    user.google_id = google_user_id
                    user.save(update_fields=['google_id'])
                
                if not user.roles:
                    return Response({
                        'status': 'onboarding_required',
                        'email': email,
                        'first_name': first_name,
                        'last_name': last_name,
                        'google_id': google_user_id,
                        'temp_token': self._generate_onboarding_token(email, google_user_id)
                    }, status=status.HTTP_200_OK)
                
                if user.roles == 'student' and not hasattr(user, 'student_profile'):
                    return Response({
                        'status': 'profile_required',
                        'roles': user.roles,
                        'email': email,
                        'temp_token': self._generate_onboarding_token(email, google_user_id)
                    }, status=status.HTTP_200_OK)
                    
            except User.DoesNotExist:
                return Response({
                    'status': 'onboarding_required',
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'google_id': google_user_id,
                    'temp_token': self._generate_onboarding_token(email, google_user_id)
                }, status=status.HTTP_200_OK)
            
            refresh = CustomTokenObtainPairSerializer.get_token(user)
            serializer = self.get_serializer(user)
            
            return Response({
                'status': 'success',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': serializer.data
            })
            
        except ValueError as e:
            logger.error(f"Google login failed: {str(e)}")
            return Response({'detail': 'Invalid Google token'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            logger.error(f"Unexpected error during Google login: {str(e)}")
            return Response({'detail': 'Authentication failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    _SECRET_KEY = None
    
    def _get_secret_key(self):
        if self._SECRET_KEY is None:
            self.__class__._SECRET_KEY = settings.SECRET_KEY
        return self._SECRET_KEY
    
    def _generate_onboarding_token(self, email, google_id):
        import jwt, time
        payload = {
            'email': email,
            'google_id': google_id,
            'exp': int(time.time()) + 3600
        }
        return jwt.encode(payload, self._get_secret_key(), algorithm='HS256')
        
    @action(detail=False, methods=['post'])
    def complete_google_onboarding(self, request):
        temp_token = request.data.get('temp_token')
        roles = request.data.get('roles')
        
        if not temp_token or not roles:
            return Response({'detail': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
        
        if roles != 'student':
            return Response({'detail': 'Invalid user type'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            import jwt
            payload = jwt.decode(temp_token, self._get_secret_key(), algorithms=['HS256'])
            email = payload.get('email')
            google_id = payload.get('google_id')
            
            profile_data = request.data.get('student_profile', {})
            if not profile_data or 'university' not in profile_data:
                return Response(
                    {'detail': 'University selection required for students'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            student_serializer = StudentProfileSerializer(data=profile_data)
            if not student_serializer.is_valid():
                return Response(student_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                user = None
                created = False
                try:
                    user = User.objects.select_for_update().get(email=email)
                    if not user.roles:
                        user.roles = roles
                        user.save(update_fields=['roles'])
                except User.DoesNotExist:
                    username = email.split('@')[0]
                    base_username = username
                    counter = 1
                    existing_usernames = list(User.objects.filter(
                        username__startswith=base_username
                    ).values_list('username', flat=True))
                    
                    while username in existing_usernames:
                        username = f"{base_username}{counter}"
                        counter += 1
                    
                    password = User.objects.make_random_password()
                    first_name = request.data.get('first_name', '')
                    last_name = request.data.get('last_name', '')
                    
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
                
                if created:
                    StudentProfile.objects.create(user=user, **profile_data)
                else:
                    StudentProfile.objects.update_or_create(
                        user=user,
                        defaults=profile_data
                    )
            
            refresh = CustomTokenObtainPairSerializer.get_token(user)
            serializer = self.get_serializer(user)
            
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': serializer.data
            }, status=status.HTTP_200_OK)
            
        except jwt.ExpiredSignatureError:
            return Response({'detail': 'Onboarding session expired'}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.DecodeError:
            return Response({'detail': 'Invalid onboarding token'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            logger.error(f"Error completing Google onboarding: {str(e)}")
            return Response({'detail': 'Failed to complete registration'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
