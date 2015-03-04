# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0031_algorithmhistory_h_index'),
    ]

    operations = [
        migrations.AddField(
            model_name='measurementhistory',
            name='active_clients',
            field=models.TextField(default=None, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='measurementhistory',
            name='passive_clients',
            field=models.TextField(default=None, null=True),
            preserve_default=True,
        ),
    ]
