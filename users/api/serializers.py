from rest_framework import serializers
from django.contrib.auth import get_user_model
from users.models import StudentProfile
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from universities.api.serializers import UniversitySerializer

User = get_user_model()

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
    
    def get_student_profile(self, obj):
        """
        Get the student profile data if it exists
        """
        if hasattr(obj, 'student_profile') and obj.student_profile:
            return StudentProfileSerializer(obj.student_profile, context=self.context).data
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

class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    university_details = UniversitySerializer(source='university', read_only=True)
    
    class Meta:
        model = StudentProfile
        fields = ['id', 'university', 'university_details', 'course', 
                  'created_at', 'updated_at', 'user']
        read_only_fields = ['id', 'created_at', 'updated_at', 'user', 'university_details']
        extra_kwargs = {
            'university': {'write_only': True}
        }

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        token['roles'] = user.roles
        token['email'] = user.email
        token['name'] = f"{user.first_name} {user.last_name}"
        
        return token