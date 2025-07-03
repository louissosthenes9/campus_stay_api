from rest_framework import serializers
from django.contrib.auth import get_user_model
from users.models import StudentProfile
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from universities.api.serializers import UniversitySerializer
from drf_spectacular.utils import extend_schema_field
from typing import Optional, Dict, Any

User = get_user_model()

class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user serializer without student_profile to avoid circular reference"""
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'mobile', 'roles', 'profile_pic', 'date_joined']
        read_only_fields = ['id', 'date_joined']

class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    university_details = UniversitySerializer(source='university', read_only=True)
    
    class Meta:
        model = StudentProfile
        fields = ['id', 'university', 'university_details', 'course', 
                  'created_at', 'updated_at', 'user']
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'university_details']
        extra_kwargs = {
            'university': {'write_only': True}
        }

class UserSerializer(serializers.ModelSerializer):
    student_profile = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'mobile', 'last_name',
                  'password', 'roles', 'profile_pic',
                  'student_profile',
                  'date_joined']
        read_only_fields = ['id', 'date_joined']
    
    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_student_profile(self, obj) -> Optional[Dict[str, Any]]:
        """
        Get the student profile data if it exists (without nested user to avoid circular reference)
        """
        if hasattr(obj, 'student_profile') and obj.student_profile:
            # Create a simplified version without the user field to avoid circular reference
            profile_data = {
                'id': obj.student_profile.id,
                'university': obj.student_profile.university_id,
                'course': obj.student_profile.course,
                'created_at': obj.student_profile.created_at,
                'updated_at': obj.student_profile.updated_at,
            }
            
            # Add university details if available
            if obj.student_profile.university:
                university_serializer = UniversitySerializer(obj.student_profile.university)
                profile_data['university_details'] = university_serializer.data
            
            return profile_data
        return None
    
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

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        token['roles'] = user.roles
        token['email'] = user.email
        token['name'] = f"{user.first_name} {user.last_name}"
        
        return token