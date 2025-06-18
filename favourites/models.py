from django.db import models

class Favourites(models.Model):
    property = models.ForeignKey('properties.Properties', on_delete=models.CASCADE, related_name='favourites')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='favourites')
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.full_name} favorited {self.property.title}"
    
    class Meta:
        unique_together = ('property', 'user')

