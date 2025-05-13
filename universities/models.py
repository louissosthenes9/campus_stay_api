from django.db import models
from django.contrib.gis.db import models as gis_models

class University(models.Model):
    name = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='university_logos/',null=True,blank=True)
    address = models.TextField()
    website = models.URLField()
    location = gis_models.PointField(srid=4326)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    class Meta:
        verbose_name_plural = 'Universities'

class Campus(models.Model):
    name = models.CharField(max_length=255)
    university = models.ForeignKey(University,on_delete=models.CASCADE,related_name='campuses')
    address = models.TextField()
    location = gis_models.PointField(srid=4326)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    class Meta:
        verbose_name_plural = 'Campuses'
