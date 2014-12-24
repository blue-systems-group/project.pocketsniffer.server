# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0009_auto_20141223_2144'),
    ]

    operations = [
        migrations.AlterField(
            model_name='algorithmhistory',
            name='celery_task_id',
            field=models.CharField(default=None, max_length=512, null=True),
            preserve_default=True,
        ),
    ]
