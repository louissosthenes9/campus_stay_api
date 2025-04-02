from django.db import models

# Create your models here.

class Conversation(models.Model):
    property = models.ForeignKey('apps.properties.Properties', on_delete=models.CASCADE, related_name='user_messages')
    student = models.ForeignKey('apps.users.User', on_delete=models.CASCADE, related_name='student_user_messages')
    broker = models.ForeignKey('apps.users.User', on_delete=models.CASCADE, related_name='broker_user_messages')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Conversation between {self.student.full_name} and {self.broker.full_name} about {self.property.title}"
    class Meta:
        unique_together = ('property', 'student', 'broker')


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey('apps.users.User', on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Message from {self.sender.full_name} in {self.conversation}"
