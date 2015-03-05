from django.core.management.base import BaseCommand

from apps.controller.graph import do_plot

class Command(BaseCommand):

  def handle(self, *args, **options):
    do_plot()
