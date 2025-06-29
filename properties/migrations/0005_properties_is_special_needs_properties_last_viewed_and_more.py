# Generated by Django 5.1.7 on 2025-06-18 10:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0004_remove_properties_broker'),
    ]

    operations = [
        migrations.AddField(
            model_name='properties',
            name='is_special_needs',
            field=models.BooleanField(blank=True, default=False, help_text='Indicates if the property is suitable for special needs', null=True),
        ),
        migrations.AddField(
            model_name='properties',
            name='last_viewed',
            field=models.DateTimeField(blank=True, help_text='Last time the property was viewed', null=True),
        ),
        migrations.AddField(
            model_name='properties',
            name='view_count',
            field=models.IntegerField(blank=True, default=0, help_text='Number of times the property has been viewed', null=True),
        ),
    ]
