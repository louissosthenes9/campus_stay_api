# universities/management/commands/seed_universities.py
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from universities.models import University

class Command(BaseCommand):
    help = "Seed sample universities into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing universities before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            University.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Cleared all universities."))

        universities_data = [
            {
                'name': 'Water Institute',
                'address': 'University Rd, Dar es Salaam',
                'website': 'http://www.waterinstitute.ac.tz/',
                'location': Point(39.2058728, -6.7882314, srid=4326),  # Note: Point takes (longitude, latitude)
            },
            {
                'name': 'National Institute of Transport',
                'address': 'P.O. Box 705 Mabibo Rd., Dar es Salaam',
                'website': 'http://www.nit.ac.tz/',
                'location': Point(39.2180425, -6.8041316, srid=4326),
            },
            {
                'name': 'DarTU',
                'address': '66RJ+2RC, CocaCola Rd, Dar es Salaam',
                'website': 'http://www.tudarco.ac.tz/',
                'location': Point(39.2140017, -6.7599428, srid=4326),
            },
            {
                'name': 'Mwalimu Nyerere Memorial International University',
                'address': '58C2+Q5P, Dar es Salaam',
                'website': 'http://www.mnma.ac.tz/',
                'location': Point(39.2764591, -6.8154102, srid=4326),
            },
            {
                'name': 'University of Dar Es Salaam - Main Campus',
                'address': 'University of Dar es Salaam',
                'website': 'https://www.udsm.ac.tz/',
                'location': Point(39.199991, -6.7777005, srid=4326),
            },
            {
                'name': 'Institute of Finance and Management',
                'address': '5 Shaaban Robert St, Dar es Salaam',
                'website': 'https://ifm.ac.tz',
                'location': Point(39.2909708, -6.8140108, srid=4326),
            },
            {
                'name': 'Ardhi University Tanzania',
                'address': 'Survey St, Dar es Salaam',
                'website': 'https://www.aru.ac.tz',
                'location': Point(39.2112763, -6.7664742, srid=4326),
            },
            {
                'name': 'Dar es Salaam Institute of Technology',
                'address': 'Morogoro Rd, Dar es Salaam',
                'website': 'https://www.dit.ac.tz',
                'location': Point(39.2710104, -6.8148071, srid=4326),
            },
        ]

        created_count = 0
        for data in universities_data:
            _, created = University.objects.get_or_create(
                name=data["name"], 
                defaults=data
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully seeded {created_count} universities.")
        )