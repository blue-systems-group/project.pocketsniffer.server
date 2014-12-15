# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0005_auto_20141215_2015'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='latency',
            name='ap',
        ),
        migrations.AlterField(
            model_name='latency',
            name='host',
            field=models.CharField(default=None, max_length=128, null=True),
            preserve_default=True,
        ),
    ]
