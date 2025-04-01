
from rest_framework import serializers
from django.contrib.auth import get_user_model
from users.models import StudentProfile, BrokerProfile
from universities.models import University

User = get_user_model()

class StudentProfileSerializer(serializers.ModelSerializer):
    university_name = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentProfile
        fields = ['university', 'course', 'year', 'university_name']
        extra_kwargs = {
            'university': {'write_only': True}
        }
    
    def get_university_name(self, obj):
        return obj.university.name if obj.university else None

class BrokerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrokerProfile

class UserSerializer(serializers.ModelSerializer):
    student_profile = StudentProfileSerializer(read_only=True)
    broker_profile = BrokerProfileSerializer(read_only=True)
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 
                  'password', 'user_type', 'phone_number', 'profile_pic',
                  'student_profile', 'broker_profile', 'email_verified',
                  'date_joined']
        read_only_fields = ['id', 'date_joined', 'email_verified']
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        
        return super().update(instance, validated_data)