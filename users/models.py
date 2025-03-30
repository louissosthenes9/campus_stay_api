from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('student','Student'),
        ('broker','Broker'),
        ('admin','Admin'),
    )
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255,blank=True,null=True)
    password = models.CharField(max_length=255)
    mobile = models.CharField(max_length=15)
    user_type=models.CharField(choices=USER_TYPE_CHOICES,max_length=10)
    profile_pic = models.ImageField(upload_to='profile_pics/',null=True,blank=True)
    email_verified = models.BooleanField(default=False)

    REQUIRED_FIELDS = ['email','mobile','user_type']

    def __str__(self):
        return self.full_name
    

class StudentProfile(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name='student_profile')
    university = models.ForeignKey('universities.University',on_delete=models.CASCADE)
    course = models.CharField(max_length=255)
    year = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.full_name
    
