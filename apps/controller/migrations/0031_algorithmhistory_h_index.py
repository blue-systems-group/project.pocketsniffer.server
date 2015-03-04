# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0030_traffic_bytes'),
    ]

    operations = [
        migrations.AddField(
            model_name='algorithmhistory',
            name='h_index',
            field=models.TextField(default=None, null=True),
            preserve_default=True,
        ),
    ]
