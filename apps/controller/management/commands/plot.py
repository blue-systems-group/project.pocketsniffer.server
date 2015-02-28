from django.core.management.base import BaseCommand

from apps.controller.graph import ALL_FIGURES

class Command(BaseCommand):

  def handle(self, *args, **options):
    for f in ALL_FIGURES:
      self.stdout.write("Plotting %s" % f.__name__)
      f().plot()
