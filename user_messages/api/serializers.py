from rest_framework import serializers
from user_messages.models import Enquiry, EnquiryMessage, EnquiryStatus
from users.api.serializers import  StudentProfileSerializer as UserProfileSerializer
from properties.api.serializers import PropertiesSerializer

class EnquiryMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_id = serializers.PrimaryKeyRelatedField(source='sender', read_only=True)
    
    class Meta:
        model = EnquiryMessage
        fields = ['id', 'content', 'sender_id', 'sender_name', 'created_at', 'is_read']
        read_only_fields = ['id', 'created_at', 'is_read', 'sender_id', 'sender_name']
        ordering = ['created_at']

class EnquirySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    property_details = PropertiesSerializer(source='property', read_only=True)
    student_details = UserProfileSerializer(source='student', read_only=True)
    messages = EnquiryMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Enquiry
        fields = [
            'id', 'property', 'property_details', 'student', 'student_details',
            'status', 'status_display', 'created_at', 'updated_at', 'is_active', 'messages'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_active', 'student']

class CreateEnquirySerializer(serializers.ModelSerializer):
    message = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = Enquiry
        fields = ['property', 'message']
    
    def create(self, validated_data):
        message_content = validated_data.pop('message')
        student_profile = self.context['request'].user.student_profile
        
        # Create the enquiry
        enquiry = Enquiry.objects.create(
            property=validated_data['property'],
            student=student_profile
        )
        
        # Create the first message
        EnquiryMessage.objects.create(
            enquiry=enquiry,
            sender=self.context['request'].user,
            content=message_content
        )
        
        return enquiry
