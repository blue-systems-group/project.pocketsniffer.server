# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0025_auto_20150228_0107'),
    ]

    operations = [
        migrations.AddField(
            model_name='traffic',
            name='corrupted_packets',
            field=models.BigIntegerField(default=None, null=True),
            preserve_default=True,
        ),
    ]
