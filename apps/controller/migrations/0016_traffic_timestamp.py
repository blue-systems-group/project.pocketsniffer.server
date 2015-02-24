# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0015_auto_20150120_2316'),
    ]

    operations = [
        migrations.AddField(
            model_name='traffic',
            name='timestamp',
            field=models.DateTimeField(default=None, null=True),
            preserve_default=True,
        ),
    ]
