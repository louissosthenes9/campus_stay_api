from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from apps.users.api.views import UserViewSet
from apps.users.models import StudentProfile, BrokerProfile
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()


class UserViewSetTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            'email': 'test@example.com',
            'password': 'testpassword123',
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'student'
        }
        
        # Create a test user for authenticated requests
        self.test_user = User.objects.create_user(
            email='existing@example.com',
            password='existingpassword',
            first_name='Existing',
            last_name='User'
        )
        
    def test_get_permissions(self):
        """Test permissions based on action type"""
        viewset = UserViewSet()
        
        # Test create action permissions
        viewset.action = 'create'
        self.assertEqual(viewset.get_permissions()[0].__class__.__name__, 'AllowAny')
        
        # Test other actions permissions
        viewset.action = 'list'
        self.assertEqual(viewset.get_permissions()[0].__class__.__name__, 'IsAuthenticated')
        
    @patch('users.api.views.send_mail')
    def test_create_student_user(self, mock_send_mail):
        """Test creating a user with student profile"""
        student_data = self.user_data.copy()
        student_data['student_profile'] = {
            'university': 'Test University',
            'major': 'Computer Science',
            'year': 3
        }
        
        url = reverse('user-list')
        response = self.client.post(url, student_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 2)  # Including the test user
        self.assertEqual(StudentProfile.objects.count(), 1)
        self.assertEqual(BrokerProfile.objects.count(), 0)
        
        # Check that send_mail was called
        mock_send_mail.assert_called_once()
        
    @patch('users.api.views.send_mail')
    def test_create_broker_user(self, mock_send_mail):
        """Test creating a user with broker profile"""
        broker_data = self.user_data.copy()
        broker_data['user_type'] = 'broker'

        url = reverse('user-list')
        response = self.client.post(url, broker_data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 2)  # Including the test user
        self.assertEqual(StudentProfile.objects.count(), 0)
        self.assertEqual(BrokerProfile.objects.count(), 1)
        mock_send_mail.assert_called_once()
    def test_me_endpoint_authenticated(self):
        """Test the me endpoint returns user data when authenticated"""
        self.client.force_authenticate(user=self.test_user)
        url = reverse('user-me')
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.test_user.email)
        
    def test_me_endpoint_unauthenticated(self):
        """Test the me endpoint returns 401 when not authenticated"""
        url = reverse('user-me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    @patch('users.api.views.default_token_generator.check_token')
    def test_verify_email_success(self, mock_check_token):
        """Test successful email verification"""
        mock_check_token.return_value = True
        
        uid = urlsafe_base64_encode(force_bytes(self.test_user.pk))
        token = "fake-token"
        
        url = reverse('user-verify-email')
        data = {'uid': uid, 'token': token}
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.test_user.refresh_from_db()
        self.assertTrue(self.test_user.email_verified)
        
    @patch('users.api.views.default_token_generator.check_token')
    def test_verify_email_invalid_token(self, mock_check_token):
        """Test email verification with invalid token"""