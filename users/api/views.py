from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, StudentProfileSerializer, BrokerProfileSerializer
from users.models import StudentProfile, BrokerProfile
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Create profile based on user type
        if user.user_type == 'student':
            student_data = request.data.get('student_profile', {})
            student_serializer = StudentProfileSerializer(data=student_data)
            if student_serializer.is_valid():
                student_serializer.save(user=user)
        
        elif user.user_type == 'broker':
            broker_data = request.data.get('broker_profile', {})
            broker_serializer = BrokerProfileSerializer(data=broker_data)
            if broker_serializer.is_valid():
                broker_serializer.save(user=user)
        
        # Send verification email
        self._send_verification_email(user)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        response_data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': serializer.data
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    def _send_verification_email(self, user):
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
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def verify_email(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        
        try:
            uid = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        
        if user is not None and default_token_generator.check_token(user, token):
            user.email_verified = True
            user.save()
            return Response({'detail': 'Email verified successfully'}, status=status.HTTP_200_OK)
        
        return Response({'detail': 'Invalid verification link'}, status=status.HTTP_400_BAD_REQUEST)