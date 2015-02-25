# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0022_auto_20150225_0129'),
    ]

    operations = [
        migrations.AddField(
            model_name='measurementhistory',
            name='algo',
            field=models.CharField(default=None, max_length=128, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='measurementhistory',
            name='measurement',
            field=models.CharField(default=None, max_length=128, null=True),
            preserve_default=True,
        ),
    ]
