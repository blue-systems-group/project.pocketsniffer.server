# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0016_traffic_timestamp'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='traffic',
            name='for_sta',
        ),
        migrations.AddField(
            model_name='traffic',
            name='for_devices',
            field=models.TextField(default=None, null=True, blank=True),
            preserve_default=True,
        ),
    ]
