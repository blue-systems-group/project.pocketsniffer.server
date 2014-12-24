# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0008_algorithmhistory_apconfighistory'),
    ]

    operations = [
        migrations.AlterField(
            model_name='algorithmhistory',
            name='begin',
            field=models.DateTimeField(default=None, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='algorithmhistory',
            name='celery_task_id',
            field=models.IntegerField(default=None, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='algorithmhistory',
            name='end',
            field=models.DateTimeField(default=None, null=True),
            preserve_default=True,
        ),
    ]
