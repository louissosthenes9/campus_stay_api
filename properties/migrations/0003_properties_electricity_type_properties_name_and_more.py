# Generated by Django 5.1.7 on 2025-05-14 11:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0002_properties_is_fenced_properties_size_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='properties',
            name='electricity_type',
            field=models.CharField(blank=True, choices=[('Submetered', 'Submetered'), ('Shared', 'Shared'), ('Individual', 'Individual'), ('None', 'None')], null=True),
        ),
        migrations.AddField(
            model_name='properties',
            name='name',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='properties',
            name='water_supply',
            field=models.BooleanField(blank=True, default=False, help_text='Indicates if water supply is available', null=True),
        ),
        migrations.AddField(
            model_name='properties',
            name='windows_type',
            field=models.CharField(blank=True, choices=[('Aluminum', 'Aluminum'), ('Nyavu', 'Nyavu')], null=True),
        ),
    ]
