# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0028_measurementhistory_ap'),
    ]

    operations = [
        migrations.AddField(
            model_name='measurementhistory',
            name='client_num',
            field=models.IntegerField(default=None, null=True),
            preserve_default=True,
        ),
    ]
