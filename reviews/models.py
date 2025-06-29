from django.db import models

class PropertyReview(models.Model):
    property = models.ForeignKey('properties.Properties', on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='property_reviews')
    rating = models.FloatField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Review by {self.reviewer.full_name} for {self.property.title}"
