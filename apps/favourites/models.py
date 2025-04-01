from django.db import models

# Create your models here.
class Favourites(models.Model):
    property = models.ForeignKey('apps.properties.Properties', on_delete=models.CASCADE, related_name='favourites')
    user = models.ForeignKey('apps.users.User', on_delete=models.CASCADE, related_name='favourites')
    addetd_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.full_name} favorited {self.property.title}"
    
    class Meta:
        unique_together = ('property', 'user')

