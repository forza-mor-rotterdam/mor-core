from apps.locatie.tasks import update_locatie_zoek_field_task
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Updates the locatie_zoek_field for all Locatie objects"

    def handle(self, *args, **options):
        task = update_locatie_zoek_field_task.delay()
        self.stdout.write(
            self.style.SUCCESS(f"Task has been queued. Task ID: {task.id}")
        )
