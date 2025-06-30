from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import User,StudentProfile as UserProfile

class EnquiryStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    IN_PROGRESS = 'in_progress', 'In Progress'
    RESOLVED = 'resolved', 'Resolved'
    CANCELLED = 'cancelled', 'Cancelled'

class Enquiry(models.Model):
    property = models.ForeignKey('properties.Properties', on_delete=models.CASCADE, related_name='enquiries')
    student = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='enquiries')
    status = models.CharField(
        max_length=20, 
        choices=EnquiryStatus.choices, 
        default=EnquiryStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Enquiries"
        ordering = ['-created_at']
        unique_together = ('property', 'student')
    
    def __str__(self):
        return f"Enquiry about {self.property.title} by {self.student.user.get_full_name()}"

class EnquiryMessage(models.Model):
    enquiry = models.ForeignKey(Enquiry, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='enquiry_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender.get_full_name()} in enquiry {self.enquiry.id}"
    
    def save(self, *args, **kwargs):
        # Update the enquiry's updated_at timestamp when a new message is added
        self.enquiry.updated_at = timezone.now()
        self.enquiry.save()
        super().save(*args, **kwargs)