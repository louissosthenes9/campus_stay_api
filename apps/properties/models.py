from django.db import models
from django.contrib.gis.db import models as gis_models

class Properties(models.Model):
    PROPERTY_TYPE_CHOICES= (
        ('house', 'House'),
        ('apartment', 'Apartment'),
        ('hostel', 'Hostel'),
        ('shared_room', 'Shared Room'),
        ('single_room', 'Single Room'),         
        ('master_bedroom', 'Master Bedroom'),   
        ('self_contained', 'Self Contained'),
        ('condo', 'Condo'),
    )
    title = models.CharField(max_length=100) 
    description = models.TextField()
    broker=models.ForeignKey('apps.users.User', on_delete=models.CASCADE, related_name='properties')
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    bedrooms = models.PositiveIntegerField(blank=True,null=True)
    toilets = models.PositiveIntegerField(null=True, blank=True)
    address = models.CharField(max_length=100)          
    location = gis_models.PointField(srid=4326)
    available_from = models.DateField()
    lease_duration = models.PositiveIntegerField(help_text="Lease duration in months")
    is_furnished = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)

    #### scores for ML
    safety_score = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    transportation_score = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    amenities_score = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    overall_score = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)

    #### timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    class Meta:
        verbose_name_plural = "Properties"
        indexes = [
            models.Index(fields=['property_type']),
            models.Index(fields=['bedrooms']),
            models.Index(fields=['price']),
        ]

class PropertyMedia(models.Model):
    MEDIA_TYPE_CHOICES = (
        ('image', 'Image'),
        ('video', 'Video'),
    )
    property = models.ForeignKey('apps.properties.Properties', on_delete=models.CASCADE, related_name='media')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='image')
    file = models.FileField(upload_to='properties/')
    media_hash = models.CharField(max_length=100, blank=True, null=True)    
    display_order = models.PositiveIntegerField(blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Property Media"
        indexes = [
            models.Index(fields=['is_primary']),
            models.Index(fields=['media_type']),
        ]

class Amenity(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Amenities"   


class PropertyAmenity(models.Model):
    property = models.ForeignKey('apps.properties.Properties', on_delete=models.CASCADE, related_name='amenities')
    amenity = models.ForeignKey('apps.properties.Amenity', on_delete=models.CASCADE, related_name='properties')

    def __str__(self):
        return f"{self.property.title} - {self.amenity.name}"

    class Meta:
        verbose_name_plural = "Property Amenities"
        unique_together = ('property', 'amenity')

class NearByPlaces(models.Model):
    PLACE_TYPE_CHOICES = (
        ('university', 'University'),
        ('transport', 'Transport Hub'),
        ('grocery', 'Grocery Store'),
        ('restaurant', 'Restaurant'),
        ('cafe', 'Cafe'),
        ('gym', 'Gym'),
        ('library', 'Library'),
        ('park', 'Park'),
        ('hospital', 'Hospital'),
        ('pharmacy', 'Pharmacy'),
    )
    
    name = models.CharField(max_length=200)
    place_type = models.CharField(max_length=20, choices=PLACE_TYPE_CHOICES)
    location = gis_models.PointField(srid=4326)
    address = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} ({self.get_place_type_display()})"
    
class PropertyNearByPlaces(models.Model):
    property = models.ForeignKey('apps.properties.Properties', on_delete=models.CASCADE, related_name='nearby_places')
    place = models.ForeignKey('apps.properties.NearByPlaces', on_delete=models.CASCADE, related_name='properties')
    distance = models.DecimalField(max_digits=5, decimal_places=2, help_text="Distance in kilometers")
    walking_time = models.PositiveIntegerField(help_text="Walking time in minutes")

    def __str__(self):
        return f"{self.property.title} - {self.place.name}"

    class Meta:
        verbose_name_plural = "Property NearBy Places"
        unique_together = ('property', 'place')

