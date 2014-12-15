# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0006_auto_20141215_2220'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='throughput',
            name='ap',
        ),
    ]
