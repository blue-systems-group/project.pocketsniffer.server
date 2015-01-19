# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0012_auto_20150119_1605'),
    ]

    operations = [
        migrations.AlterField(
            model_name='traffic',
            name='for_sta',
            field=models.ForeignKey(related_name='for_station', default=None, to='controller.Station', null=True),
            preserve_default=True,
        ),
    ]
