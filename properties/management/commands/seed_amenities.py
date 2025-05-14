from django.core.management.base import BaseCommand
from properties.models import Amenity

class Command(BaseCommand):
    help = 'Seed initial amenities data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing amenities before seeding'
        )

    def handle(self, *args, **options):
        amenities = [
            {'name': 'Wi-Fi', 'description': 'High-speed internet access', 'icon': 'CiWifiOn'},
            {'name': 'Parking', 'description': 'Dedicated parking space', 'icon': 'LuCircleParking'},
            {'name': 'Swimming Pool', 'description': 'Private or shared pool', 'icon': 'PiSwimmingPoolLight'},
            {'name': 'Gym', 'description': 'Fitness center', 'icon': 'MdFitnessCenter'},
            {'name': 'AC', 'description': 'Air conditioning', 'icon': 'TbAirConditioning'},
            {'name': 'Security', 'description': '24/7 security', 'icon': 'MdOutlineSecurity'},
            {'name': 'Laundry', 'description': 'Laundry facilities', 'icon': 'MdOutlineLocalLaundryService'},
            {'name': 'Furnished', 'description': 'Fully furnished rooms', 'icon': 'LiaCouchSolid'},
            {'name': 'Balcony', 'description': 'Private balcony', 'icon': 'MdBalcony'},
            {'name': 'Pet Friendly', 'description': 'Pet-friendly accommodation', 'icon': 'MdPets'},
        ]

        if options['clear']:
            self.stdout.write(self.style.WARNING("Deleting all existing amenities..."))
            Amenity.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("All amenities deleted."))

        created_count = 0
        for amenity_data in amenities:
            obj, created = Amenity.objects.get_or_create(
                name=amenity_data['name'],
                defaults=amenity_data
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded {created_count} new amenities. "
            f"Total amenities now: {Amenity.objects.count()}"
        ))
