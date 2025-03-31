from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission

class User(AbstractUser):
    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_set",  # Avoids conflict
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_set_permissions",  # Avoids conflict
        blank=True
    )

    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('broker', 'Broker'),
        ('admin', 'Admin'),
    )

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    password = models.CharField(max_length=255)
    mobile = models.CharField(max_length=15)
    user_type = models.CharField(choices=USER_TYPE_CHOICES, max_length=10)
    profile_pic = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    email_verified = models.BooleanField(default=False)

    REQUIRED_FIELDS = ['email', 'mobile', 'user_type']

    def __str__(self):
        return self.full_name or self.username  # Fallback in case full_name is empty


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    university = models.ForeignKey('universities.University', on_delete=models.CASCADE)
    course = models.CharField(max_length=255)
    year = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.full_name or self.user.username


class BrokerProfile(models.Model):   
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='broker_profile')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.full_name or self.user.username
