from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission

class User(AbstractUser):
    username = models.CharField(max_length=150, unique=True,null=True, blank=True)  # Ensure username is unique and required
    email = models.EmailField(unique=True, null=False,db_index=True)  # Ensure email is unique and required

    full_name = models.CharField(max_length=255, blank=True, null=True)
    mobile = models.CharField(max_length=15)
    google_id = models.CharField(max_length=255, null=True, blank=True)
    ROLES = (
        ('student', 'Student'),
        ('broker', 'Broker'),
        ('admin', 'Admin'),
    )
    roles = models.CharField(choices=ROLES, max_length=10)
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
    REQUIRED_FIELDS = ['mobile', 'roles'] 

    def __str__(self):
        return self.full_name or self.email  

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
