from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, StudentProfileSerializer, BrokerProfileSerializer
from users.models import StudentProfile, BrokerProfile
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
import logging

# Configure logging
logger = logging.getLogger(__name__)

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'verify_email']:
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
                
                # Save the user
                user = user_serializer.save()
                logger.info(f"User created successfully: {user.username} ({user.pk})")
                
                # Handle profile creation based on user type
                if user.user_type == 'student':
                    self._create_student_profile(request, user)
                elif user.user_type == 'broker':
                    self._create_broker_profile(request, user)
                else:
                    logger.warning(f"Unknown user_type: {user.user_type}")
                
                # Send verification email
                try:
                    self._send_verification_email(user)
                    logger.info(f"Verification email sent to: {user.email}")
                except Exception as e:
                    logger.error(f"Failed to send verification email: {str(e)}")
                    # Continue despite email sending failure
                
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
                # Could create the university here if required
        
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
    
    def _send_verification_email(self, user):
        """Send an email verification link to the user."""
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{uid}/{token}/"
        
        send_mail(
            subject="Verify your email address",
            message=f"Please click the link to verify your email: {verification_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    
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
    def verify_email(self, request):
        """Verify a user's email address using the token from the verification link."""
        uid = request.data.get('uid')
        token = request.data.get('token')
        
        if not uid or not token:
            return Response(
                {'detail': 'Both uid and token are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            uid = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=uid)
            logger.info(f"Email verification attempt for user: {user.pk}")
        except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
            logger.warning(f"Invalid uid in email verification: {uid}, Error: {str(e)}")
            user = None
        
        if user is not None and default_token_generator.check_token(user, token):
            if user.email_verified:
                logger.info(f"User {user.pk} email already verified")
                return Response(
                    {'detail': 'Email already verified'}, 
                    status=status.HTTP_200_OK
                )
                
            user.email_verified = True
            user.save()
            logger.info(f"User {user.pk} email verified successfully")
            return Response(
                {'detail': 'Email verified successfully'}, 
                status=status.HTTP_200_OK
            )
        
        logger.warning(f"Invalid verification token for user: {uid if user else 'unknown'}")
        return Response(
            {'detail': 'Invalid verification link'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=False, methods=['post'])
    def resend_verification(self, request):
        """Resend the verification email to the authenticated user."""
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        if request.user.email_verified:
            return Response(
                {"detail": "Email already verified"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            self._send_verification_email(request.user)
            return Response(
                {"detail": "Verification email sent successfully"}, 
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Failed to resend verification email: {str(e)}")
            return Response(
                {"detail": "Failed to send verification email"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )