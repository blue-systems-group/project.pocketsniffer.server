# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0026_traffic_corrupted_packets'),
    ]

    operations = [
        migrations.AlterField(
            model_name='traffic',
            name='src',
            field=models.CharField(default=None, max_length=17, null=True, db_index=True),
            preserve_default=True,
        ),
    ]
