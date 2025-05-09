# Generated by Django 5.1.7 on 2025-03-31 18:13

import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Amenity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('icon', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'Amenities',
            },
        ),
        migrations.CreateModel(
            name='NearByPlaces',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('place_type', models.CharField(choices=[('university', 'University'), ('transport', 'Transport Hub'), ('grocery', 'Grocery Store'), ('restaurant', 'Restaurant'), ('cafe', 'Cafe'), ('gym', 'Gym'), ('library', 'Library'), ('park', 'Park'), ('hospital', 'Hospital'), ('pharmacy', 'Pharmacy')], max_length=20)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('address', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Properties',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('property_type', models.CharField(choices=[('house', 'House'), ('apartment', 'Apartment'), ('hostel', 'Hostel'), ('shared_room', 'Shared Room'), ('single_room', 'Single Room'), ('master_bedroom', 'Master Bedroom'), ('self_contained', 'Self Contained'), ('condo', 'Condo')], max_length=20)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('bedrooms', models.PositiveIntegerField(blank=True, null=True)),
                ('toilets', models.PositiveIntegerField(blank=True, null=True)),
                ('address', models.CharField(max_length=100)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('available_from', models.DateField()),
                ('lease_duration', models.PositiveIntegerField(help_text='Lease duration in months')),
                ('is_furnished', models.BooleanField(default=False)),
                ('is_available', models.BooleanField(default=True)),
                ('safety_score', models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ('transportation_score', models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ('amenities_score', models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ('overall_score', models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('broker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='properties', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Properties',
            },
        ),
        migrations.CreateModel(
            name='PropertyAmenity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amenity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='properties', to='properties.amenity')),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='amenities', to='properties.properties')),
            ],
            options={
                'verbose_name_plural': 'Property Amenities',
            },
        ),
        migrations.CreateModel(
            name='PropertyMedia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('media_type', models.CharField(choices=[('image', 'Image'), ('video', 'Video')], default='image', max_length=10)),
                ('file', models.FileField(upload_to='properties/')),
                ('media_hash', models.CharField(blank=True, max_length=100, null=True)),
                ('display_order', models.PositiveIntegerField(blank=True, null=True)),
                ('is_primary', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='media', to='properties.properties')),
            ],
            options={
                'verbose_name_plural': 'Property Media',
            },
        ),
        migrations.CreateModel(
            name='PropertyNearByPlaces',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('distance', models.DecimalField(decimal_places=2, help_text='Distance in kilometers', max_digits=5)),
                ('walking_time', models.PositiveIntegerField(help_text='Walking time in minutes')),
                ('place', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='properties', to='properties.nearbyplaces')),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='nearby_places', to='properties.properties')),
            ],
            options={
                'verbose_name_plural': 'Property NearBy Places',
            },
        ),
        migrations.AddIndex(
            model_name='properties',
            index=models.Index(fields=['property_type'], name='properties__propert_98eeee_idx'),
        ),
        migrations.AddIndex(
            model_name='properties',
            index=models.Index(fields=['bedrooms'], name='properties__bedroom_1f3b81_idx'),
        ),
        migrations.AddIndex(
            model_name='properties',
            index=models.Index(fields=['price'], name='properties__price_91ef21_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='propertyamenity',
            unique_together={('property', 'amenity')},
        ),
        migrations.AddIndex(
            model_name='propertymedia',
            index=models.Index(fields=['is_primary'], name='properties__is_prim_d2f2f2_idx'),
        ),
        migrations.AddIndex(
            model_name='propertymedia',
            index=models.Index(fields=['media_type'], name='properties__media_t_10e890_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='propertynearbyplaces',
            unique_together={('property', 'place')},
        ),
    ]
