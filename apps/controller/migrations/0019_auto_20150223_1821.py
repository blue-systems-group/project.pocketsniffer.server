# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0018_auto_20150217_1713'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='latency',
            name='station',
        ),
        migrations.DeleteModel(
            name='Latency',
        ),
        migrations.RemoveField(
            model_name='throughput',
            name='station',
        ),
        migrations.DeleteModel(
            name='Throughput',
        ),
    ]
