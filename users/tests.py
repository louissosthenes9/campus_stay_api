import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from users.models import StudentProfile, BrokerProfile
from users.api.views import UserViewSet
from universities.models import University

User = get_user_model()

class GoogleAuthTests(TestCase):
    """Test the Google OAuth authentication flow."""
    
    def setUp(self):
        self.client = APIClient()
        self.factory = RequestFactory()
        self.google_login_url = reverse('user-google-login')
        self.onboarding_url = reverse('user-complete-google-onboarding')
        
        # Create a test university for student profiles
        self.university = University.objects.create(
            name="Test University",
            country="Test Country",
            city="Test City",
            location='POINT(0 0)'
        )

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_login_new_user(self, mock_verify_token):
        """Test Google login for a new user requiring onboarding."""
        # Mock the Google token verification
        mock_verify_token.return_value = {
            'sub': '123456789',
            'email': 'newuser@example.com',
            'given_name': 'New',
            'family_name': 'User',
        }
        
        response = self.client.post(self.google_login_url, {'token': 'valid_token'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'onboarding_required')
        self.assertEqual(response.data['email'], 'newuser@example.com')
        self.assertTrue('temp_token' in response.data)

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_login_existing_user(self, mock_verify_token):
        """Test Google login for an existing user with completed profile."""
        # Create test user with student profile
        test_user = User.objects.create_user(
            username='testuser',
            email='existinguser@example.com',
            password='testpass123',
            user_type='student',
            google_id='123456789'
        )
        
        StudentProfile.objects.create(
            user=test_user,
            university=self.university,
            course='Computer Science'
        )
        
        # Mock the Google token verification
        mock_verify_token.return_value = {
            'sub': '123456789',
            'email': 'existinguser@example.com',
            'given_name': 'Existing',
            'family_name': 'User',
        }
        
        response = self.client.post(self.google_login_url, {'token': 'valid_token'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertTrue('refresh' in response.data)
        self.assertTrue('access' in response.data)
        self.assertEqual(response.data['user']['email'], 'existinguser@example.com')

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_login_profile_required(self, mock_verify_token):
        """Test Google login for an existing user without profile."""
        # Create test user without profile
        test_user = User.objects.create_user(
            username='noprofile',
            email='noprofile@example.com',
            password='testpass123',
            user_type='student',
            google_id='987654321'
        )
        
        # Mock the Google token verification
        mock_verify_token.return_value = {
            'sub': '987654321',
            'email': 'noprofile@example.com',
            'given_name': 'No',
            'family_name': 'Profile',
        }
        
        response = self.client.post(self.google_login_url, {'token': 'valid_token'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'profile_required')
        self.assertEqual(response.data['user_type'], 'student')
        self.assertTrue('temp_token' in response.data)

    @patch('google.oauth2.id_token.verify_oauth2_token')
    def test_google_login_invalid_token(self, mock_verify_token):
        """Test Google login with invalid token."""
        # Mock the Google token verification to raise an exception
        mock_verify_token.side_effect = ValueError("Invalid token")
        
        response = self.client.post(self.google_login_url, {'token': 'invalid_token'})
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], 'Invalid Google token')

    @patch('jwt.decode')
    def test_complete_google_onboarding_new_user(self, mock_jwt_decode):
        """Test completing Google onboarding for a new user."""
        # Mock the JWT verification
        mock_jwt_decode.return_value = {
            'email': 'newuser@example.com',
            'google_id': '123456789',
        }
        
        # Onboarding data
        onboarding_data = {
            'temp_token': 'valid_token',
            'user_type': 'student',
            'first_name': 'New',
            'last_name': 'User',
            'student_profile': {
                'university': self.university.id,
                'course': 'Computer Science',
                'graduating_year': 2025
            }
        }
        
        response = self.client.post(self.onboarding_url, onboarding_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('refresh' in response.data)
        self.assertTrue('access' in response.data)
        
        # Verify user was created
        user = User.objects.get(email='newuser@example.com')
        self.assertEqual(user.user_type, 'student')
        self.assertEqual(user.google_id, '123456789')
        
        # Verify student profile was created
        profile = StudentProfile.objects.get(user=user)
        self.assertEqual(profile.university.id, self.university.id)
        self.assertEqual(profile.course, 'Computer Science')

    @patch('jwt.decode')
    def test_complete_google_onboarding_existing_user(self, mock_jwt_decode):
        """Test completing Google onboarding for an existing user."""
        # Create user without profile
        test_user = User.objects.create_user(
            username='existingonboard',
            email='existingonboard@example.com',
            password='testpass123',
            user_type='broker',
            google_id='123123123'
        )
        
        # Mock the JWT verification
        mock_jwt_decode.return_value = {
            'email': 'existingonboard@example.com',
            'google_id': '123123123',
        }
        
        # Onboarding data
        onboarding_data = {
            'temp_token': 'valid_token',
            'user_type': 'broker',
            'broker_profile': {
                'company_name': 'Test Brokerage',
                'license_number': 'BRK12345',
            }
        }
        
        response = self.client.post(self.onboarding_url, onboarding_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify broker profile was created
        profile = BrokerProfile.objects.get(user=test_user)
        self.assertEqual(profile.company_name, 'Test Brokerage')


class TraditionalAuthTests(TestCase):
    """Test the traditional username/password authentication flow."""
    
    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse('user-login')
        self.register_url = reverse('user-list')
        self.me_url = reverse('user-me')
        
        # Create a test university
        self.university = University.objects.create(
            name="Test University",
            country="Test Country",
            city="Test City",
            location='POINT(0 0)'
        )
        
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123',
            user_type='student'
        )
        
        # Create student profile
        self.profile = StudentProfile.objects.create(
            user=self.user,
            university=self.university,
            course='Computer Science'
        )

    def test_login_success(self):
        """Test successful login with correct credentials."""
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('refresh' in response.data)
        self.assertTrue('access' in response.data)
        self.assertEqual(response.data['user']['username'], 'testuser')

    def test_login_failure(self):
        """Test login failure with incorrect credentials."""
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'wrongpass'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_register_success(self):
        """Test successful user registration."""
        registration_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'user_type': 'student',
            'student_profile': {
                'university': self.university.id,
                'course': 'Physics'
            }
        }
        
        response = self.client.post(self.register_url, registration_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        
        # Verify student profile was created
        user = User.objects.get(username='newuser')
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())

    def test_me_endpoint(self):
        """Test the 'me' endpoint returns the authenticated user's details."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.me_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'testuser@example.com')
        self.assertEqual(response.data['user_type'], 'student')
        self.assertTrue('student_profile' in response.data)
        self.assertEqual(response.data['student_profile']['course'], 'Computer Science')
