from django.core.management.base import BaseCommand

from apps.controller.models import cleanup_all

class Command(BaseCommand):

  def handle(self, *args, **options):
    cleanup_all()
