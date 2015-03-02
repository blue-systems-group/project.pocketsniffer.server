# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0027_auto_20150228_1743'),
    ]

    operations = [
        migrations.AddField(
            model_name='measurementhistory',
            name='ap',
            field=models.ForeignKey(default=None, to='controller.AccessPoint', null=True),
            preserve_default=True,
        ),
    ]
