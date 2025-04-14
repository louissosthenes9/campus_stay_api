# Generated by Django 5.1.7 on 2025-04-14 18:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_remove_user_email_verified'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='studentprofile',
            name='year',
        ),
        migrations.AddField(
            model_name='brokerprofile',
            name='company_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='studentprofile',
            name='course',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
