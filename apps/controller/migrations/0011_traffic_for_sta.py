# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0010_auto_20141223_2157'),
    ]

    operations = [
        migrations.AddField(
            model_name='traffic',
            name='for_sta',
            field=models.ForeignKey(related_name='for_sta', default=None, to='controller.Station', null=True),
            preserve_default=True,
        ),
    ]
