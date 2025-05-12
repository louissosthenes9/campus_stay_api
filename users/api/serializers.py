
from rest_framework import serializers
from django.contrib.auth import get_user_model
from users.models import StudentProfile, BrokerProfile
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

User = get_user_model()

class StudentProfileSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = StudentProfile
        fields = ['university', 'course']
        extra_kwargs = {
            'university': {'write_only': True}
        }
    

class BrokerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrokerProfile
        fields = ['company_name']

class UserSerializer(serializers.ModelSerializer):
    student_profile = StudentProfileSerializer(read_only=True)
    broker_profile = BrokerProfileSerializer(read_only=True)
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'mobile','last_name', 
                  'password', 'roles','profile_pic',
                  'student_profile', 'broker_profile', 
                  'date_joined']
        read_only_fields = ['id', 'date_joined']
    
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