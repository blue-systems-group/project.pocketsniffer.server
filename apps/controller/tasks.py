from __future__ import absolute_import

import logging
from datetime import datetime as dt

from celery import shared_task


from apps.controller.models import AlgorithmHistory

logger = logging.getLogger('controller')

@shared_task(bind=True)
def run_algorithm(self, algo_cls, *args, **kwargs):
  logger.debug("Starting algorithm %s" , algo_cls.__name__)
  algo = algo_cls(*args, **kwargs)

  history = AlgorithmHistory(algo=algo_cls.__name__, begin=dt.now(), celery_task_id=self.request.id)
  history.save()

  algo.run()
