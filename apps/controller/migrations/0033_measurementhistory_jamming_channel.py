# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0032_auto_20150304_0259'),
    ]

    operations = [
        migrations.AddField(
            model_name='measurementhistory',
            name='jamming_channel',
            field=models.IntegerField(default=None, null=True),
            preserve_default=True,
        ),
    ]
