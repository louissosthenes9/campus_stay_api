from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission

class User(AbstractUser):
    username = None  # Removing username field
    email = models.EmailField(unique=True, null=False)  # Ensure email is unique and required

    full_name = models.CharField(max_length=255, blank=True, null=True)
    mobile = models.CharField(max_length=15)
    
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('broker', 'Broker'),
        ('admin', 'Admin'),
    )
    user_type = models.CharField(choices=USER_TYPE_CHOICES, max_length=10)
    profile_pic = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_set",  
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_set_permissions", 
        blank=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['mobile', 'user_type']  # Fields required when creating superusers

    def __str__(self):
        return self.full_name or self.email  # Fallback to email if full_name is empty


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    university = models.ForeignKey('universities.University', on_delete=models.CASCADE)
    course = models.CharField(max_length=255,null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.full_name or self.user.email


class BrokerProfile(models.Model):   
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='broker_profile')
    company_name = models.CharField(max_length=255,null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.full_name or self.user.email
