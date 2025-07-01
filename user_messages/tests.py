from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.utils import timezone

from properties.models import Properties
from users.models import StudentProfile
from user_messages.models import Enquiry, EnquiryMessage, EnquiryStatus

User = get_user_model()


class EnquiryModelTest(TestCase):
    def setUp(self):
        # Create a property owner
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        
        # Create a student user
        self.student_user = User.objects.create_user(
            email='student@example.com',
            password='testpass123',
            first_name='Jane',
            last_name='Smith'
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            phone_number='+1234567890',
            date_of_birth='2000-01-01',
            gender='F',
            nationality='US',
            university='Test University',
            course='Computer Science',
            year_of_study=2
        )
        
        # Create a property
        self.property = Properties.objects.create(
            title='Test Property',
            description='A test property',
            price=1000,
            address='123 Test St',
            city='Test City',
            user=self.owner
        )
    
    def test_create_enquiry(self):
        """Test creating a new enquiry"""
        enquiry = Enquiry.objects.create(
            property=self.property,
            student=self.student_profile,
            status=EnquiryStatus.PENDING
        )
        
        self.assertEqual(enquiry.property, self.property)
        self.assertEqual(enquiry.student, self.student_profile)
        self.assertEqual(enquiry.status, EnquiryStatus.PENDING)
        self.assertTrue(enquiry.is_active)
        self.assertIsNotNone(enquiry.created_at)
        self.assertIsNotNone(enquiry.updated_at)
    
    def test_enquiry_str_representation(self):
        """Test the string representation of an enquiry"""
        enquiry = Enquiry.objects.create(
            property=self.property,
            student=self.student_profile
        )
        expected_str = f"Enquiry about {self.property.title} by {self.student_profile.user.get_full_name()}"
        self.assertEqual(str(enquiry), expected_str)
    
    def test_enquiry_message_creation(self):
        """Test creating a message in an enquiry"""
        enquiry = Enquiry.objects.create(
            property=self.property,
            student=self.student_profile
        )
        
        message = EnquiryMessage.objects.create(
            enquiry=enquiry,
            sender=self.student_user,
            content='This is a test message'
        )
        
        self.assertEqual(message.enquiry, enquiry)
        self.assertEqual(message.sender, self.student_user)
        self.assertEqual(message.content, 'This is a test message')
        self.assertFalse(message.is_read)
        self.assertIsNotNone(message.created_at)
    
    def test_enquiry_message_str_representation(self):
        """Test the string representation of a message"""
        enquiry = Enquiry.objects.create(
            property=self.property,
            student=self.student_profile
        )
        message = EnquiryMessage.objects.create(
            enquiry=enquiry,
            sender=self.student_user,
            content='Test message'
        )
        expected_str = f"Message from {self.student_user.get_full_name()} in enquiry {enquiry.id}"
        self.assertEqual(str(message), expected_str)
    
    def test_message_save_updates_enquiry_updated_at(self):
        """Test that saving a message updates the enquiry's updated_at timestamp"""
        enquiry = Enquiry.objects.create(
            property=self.property,
            student=self.student_profile
        )
        
        original_updated_at = enquiry.updated_at
        
        # Add a small delay to ensure the timestamps would be different
        import time
        time.sleep(0.1)
        
        # Create a message
        message = EnquiryMessage(
            enquiry=enquiry,
            sender=self.student_user,
            content='Test message'
        )
        message.save()
        
        # Refresh the enquiry from the database
        enquiry.refresh_from_db()
        
        # The updated_at should be newer than the original
        self.assertGreater(enquiry.updated_at, original_updated_at)


class EnquiryViewSetTest(APITestCase):
    def setUp(self):
        # Create users
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        
        self.student_user = User.objects.create_user(
            email='student@example.com',
            password='testpass123',
            first_name='Jane',
            last_name='Smith'
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            phone_number='+1234567890',
            date_of_birth='2000-01-01',
            gender='F',
            nationality='US',
            university='Test University',
            course='Computer Science',
            year_of_study=2
        )
        
        # Create another student
        self.other_student = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            first_name='Other',
            last_name='Student'
        )
        self.other_student_profile = StudentProfile.objects.create(
            user=self.other_student,
            phone_number='+1987654321',
            date_of_birth='2001-01-01',
            gender='M',
            nationality='UK',
            university='Other University',
            course='Physics',
            year_of_study=3
        )
        
        # Create a property
        self.property = Properties.objects.create(
            title='Test Property',
            description='A test property',
            price=1000,
            address='123 Test St',
            city='Test City',
            user=self.owner
        )
        
        # Create some enquiries
        self.enquiry1 = Enquiry.objects.create(
            property=self.property,
            student=self.student_profile,
            status=EnquiryStatus.PENDING
        )
        
        self.enquiry2 = Enquiry.objects.create(
            property=self.property,
            student=self.other_student_profile,
            status=EnquiryStatus.IN_PROGRESS
        )
        
        # Create some messages
        EnquiryMessage.objects.create(
            enquiry=self.enquiry1,
            sender=self.student_user,
            content='First message from student'
        )
        
        EnquiryMessage.objects.create(
            enquiry=self.enquiry1,
            sender=self.owner,
            content='Reply from owner'
        )
        
        # Set up API client
        self.client = APIClient()
    
    def test_list_enquiries_as_student(self):
        """Test that a student can only see their own enquiries"""
        self.client.force_authenticate(user=self.student_user)
        
        response = self.client.get(reverse('enquiry-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.enquiry1.id)
    
    def test_list_enquiries_as_owner(self):
        """Test that a property owner can see all enquiries for their property"""
        self.client.force_authenticate(user=self.owner)
        
        response = self.client.get(reverse('enquiry-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual({e['id'] for e in response.data}, {self.enquiry1.id, self.enquiry2.id})
    
    def test_create_enquiry(self):
        """Test creating a new enquiry"""
        self.client.force_authenticate(user=self.student_user)
        
        data = {
            'property': self.property.id,
            'message': 'I am interested in this property.'
        }
        
        response = self.client.post(reverse('enquiry-list'), data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Enquiry.objects.count(), 3)
        
        # Check that the enquiry was created with the correct status
        enquiry = Enquiry.objects.latest('created_at')
        self.assertEqual(enquiry.status, EnquiryStatus.PENDING)
        self.assertEqual(enquiry.student, self.student_profile)
        
        # Check that a message was created
        self.assertEqual(enquiry.messages.count(), 1)
        message = enquiry.messages.first()
        self.assertEqual(message.content, 'I am interested in this property.')
        self.assertEqual(message.sender, self.student_user)
    
    def test_retrieve_enquiry_as_participant(self):
        """Test that a participant can retrieve an enquiry"""
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('enquiry-detail', args=[self.enquiry1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.enquiry1.id)
        self.assertEqual(len(response.data['messages']), 2)
    
    def test_retrieve_enquiry_as_non_participant(self):
        """Test that a non-participant cannot retrieve an enquiry"""
        self.client.force_authenticate(user=self.other_student)
        
        url = reverse('enquiry-detail', args=[self.enquiry1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_update_enquiry_status_as_owner(self):
        """Test that a property owner can update the status of an enquiry"""
        self.client.force_authenticate(user=self.owner)
        
        url = reverse('enquiry-detail', args=[self.enquiry1.id])
        data = {'status': EnquiryStatus.RESOLVED}
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.enquiry1.refresh_from_db()
        self.assertEqual(self.enquiry1.status, EnquiryStatus.RESOLVED)
    
    def test_cancel_enquiry_as_student(self):
        """Test that a student can cancel their own enquiry"""
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('enquiry-detail', args=[self.enquiry1.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.enquiry1.refresh_from_db()
        self.assertFalse(self.enquiry1.is_active)
        self.assertEqual(self.enquiry1.status, EnquiryStatus.CANCELLED)
    
    def test_cancel_other_students_enquiry(self):
        """Test that a student cannot cancel another student's enquiry"""
        self.client.force_authenticate(user=self.other_student)
        
        url = reverse('enquiry-detail', args=[self.enquiry1.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.enquiry1.refresh_from_db()
        self.assertTrue(self.enquiry1.is_active)
    
    def test_list_messages(self):
        """Test listing messages in an enquiry"""
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('enquiry-messages-list', kwargs={'enquiry_id': self.enquiry1.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['content'], 'First message from student')
        self.assertEqual(response.data[1]['content'], 'Reply from owner')
    
    def test_send_message(self):
        """Test sending a message in an enquiry"""
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('enquiry-messages-list', kwargs={'enquiry_id': self.enquiry1.id})
        data = {'content': 'A new message'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.enquiry1.messages.count(), 3)
        
        # Check that the message was created correctly
        message = self.enquiry1.messages.latest('created_at')
        self.assertEqual(message.content, 'A new message')
        self.assertEqual(message.sender, self.student_user)
        
        # Check that the enquiry status was updated to IN_PROGRESS
        self.enquiry1.refresh_from_db()
        self.assertEqual(self.enquiry1.status, EnquiryStatus.IN_PROGRESS)
    
    def test_mark_messages_as_read(self):
        """Test marking messages as read"""
        self.client.force_authenticate(user=self.owner)
        
        # Create an unread message
        message = EnquiryMessage.objects.create(
            enquiry=self.enquiry1,
            sender=self.student_user,
            content='Unread message',
            is_read=False
        )
        
        url = reverse('enquiry-mark-as-read', args=[self.enquiry1.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the message from the database
        message.refresh_from_db()
        self.assertTrue(message.is_read)
    
    def test_mark_messages_as_read_unauthorized(self):
        """Test that only the property owner can mark messages as read"""
        self.client.force_authenticate(user=self.student_user)
        
        url = reverse('enquiry-mark-as-read', args=[self.enquiry1.id])
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class EnquirySerializerTest(TestCase):
    def setUp(self):
        # Set up test data similar to the model tests
        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        
        self.student_user = User.objects.create_user(
            email='student@example.com',
            password='testpass123',
            first_name='Jane',
            last_name='Smith'
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            phone_number='+1234567890',
            date_of_birth='2000-01-01',
            gender='F',
            nationality='US',
            university='Test University',
            course='Computer Science',
            year_of_study=2
        )
        
        self.property = Properties.objects.create(
            title='Test Property',
            description='A test property',
            price=1000,
            address='123 Test St',
            city='Test City',
            user=self.owner
        )
        
        self.enquiry = Enquiry.objects.create(
            property=self.property,
            student=self.student_profile,
            status=EnquiryStatus.PENDING
        )
        
        self.message = EnquiryMessage.objects.create(
            enquiry=self.enquiry,
            sender=self.student_user,
            content='Test message'
        )
    
    def test_enquiry_serializer(self):
        """Test the EnquirySerializer"""
        from user_messages.api.serializers import EnquirySerializer
        
        serializer = EnquirySerializer(instance=self.enquiry)
        data = serializer.data
        
        self.assertEqual(data['id'], self.enquiry.id)
        self.assertEqual(data['status'], EnquiryStatus.PENDING)
        self.assertEqual(data['status_display'], 'Pending')
        self.assertTrue(data['is_active'])
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
        
        # Check nested property data
        self.assertEqual(data['property_details']['id'], self.property.id)
        self.assertEqual(data['property_details']['title'], self.property.title)
        
        # Check nested student data
        self.assertEqual(data['student_details']['id'], self.student_profile.id)
        
        # Check messages
        self.assertEqual(len(data['messages']), 1)
        self.assertEqual(data['messages'][0]['content'], 'Test message')
    
    def test_create_enquiry_serializer(self):
        """Test the CreateEnquirySerializer"""
        from user_messages.api.serializers import CreateEnquirySerializer
        
        data = {
            'property': self.property.id,
            'message': 'I am interested in this property.'
        }
        
        context = {'request': type('Request', (), {'user': self.student_user})}
        serializer = CreateEnquirySerializer(data=data, context=context)
        
        self.assertTrue(serializer.is_valid())
        
        enquiry = serializer.save()
        
        self.assertEqual(enquiry.property, self.property)
        self.assertEqual(enquiry.student, self.student_profile)
        self.assertEqual(enquiry.status, EnquiryStatus.PENDING)
        
        # Check that a message was created
        self.assertEqual(enquiry.messages.count(), 1)
        message = enquiry.messages.first()
        self.assertEqual(message.content, 'I am interested in this property.')
        self.assertEqual(message.sender, self.student_user)
    
    def test_enquiry_message_serializer(self):
        """Test the EnquiryMessageSerializer"""
        from user_messages.api.serializers import EnquiryMessageSerializer
        
        serializer = EnquiryMessageSerializer(instance=self.message)
        data = serializer.data
        
        self.assertEqual(data['id'], self.message.id)
        self.assertEqual(data['content'], 'Test message')
        self.assertEqual(data['sender_id'], self.student_user.id)
        self.assertEqual(data['sender_name'], self.student_user.get_full_name())
        self.assertIn('created_at', data)
        self.assertFalse(data['is_read'])
