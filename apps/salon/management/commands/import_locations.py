import json
from django.core.management.base import BaseCommand
from apps.salon.models import Province, City
from django.db import transaction


class Command(BaseCommand):
    help = "Import provinces and cities from JSON files"

    def add_arguments(self, parser):
        parser.add_argument(
            "--provinces",
            type=str,
            required=True,
            help="Path to provinces.json file"
        )
        parser.add_argument(
            "--cities",
            type=str,
            required=True,
            help="Path to provinces_cities.json file"
        )

    @transaction.atomic
    def handle(self, *args, **options):
        provinces_file = options["provinces"]
        cities_file = options["cities"]

        self.stdout.write(self.style.NOTICE("Reading JSON files..."))

        # --- Load JSON files ---
        with open(provinces_file, "r", encoding="utf-8") as f:
            provinces_data = json.load(f)

        with open(cities_file, "r", encoding="utf-8") as f:
            cities_data = json.load(f)

        self.stdout.write(self.style.NOTICE("Importing provinces..."))

        # -----------------------------
        #      IMPORT PROVINCES
        # -----------------------------
        province_map = {}  # {provinceId → Province object}

        for item in provinces_data:
            p_name = item["provinceName"].strip()
            p_id = item["provinceId"]

            province, created = Province.objects.get_or_create(name=p_name)
            province_map[p_id] = province

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created province: {p_name}"))
            else:
                self.stdout.write(self.style.WARNING(f"Province exists: {p_name}"))

        self.stdout.write(self.style.NOTICE("Importing cities..."))

        # -----------------------------
        #        IMPORT CITIES
        # -----------------------------
        for item in cities_data:
            c_name = item["cityName"].strip()
            p_id = item["provinceId"]

            if p_id not in province_map:
                raise Exception(f"Province with ID {p_id} not found for city {c_name}")

            province = province_map[p_id]

            city, created = City.objects.get_or_create(
                name=c_name,
                province=province,
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created city: {c_name}"))
            else:
                self.stdout.write(self.style.WARNING(f"City exists: {c_name}"))

        self.stdout.write(self.style.SUCCESS("\n✔ Import completed successfully!"))
