from django.core.management.base import BaseCommand
from salon.models import Appointment

class Command(BaseCommand):
    help = 'Set canceled_by field to "manager" for all canceled appointments (only for test data)'

    def handle(self, *args, **kwargs):
        appointments = Appointment.objects.filter(status='canceled', canceled_by__isnull=True)
        count = appointments.update(canceled_by='manager')
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} canceled appointments.'))
