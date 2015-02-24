# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0013_auto_20150119_1810'),
    ]

    operations = [
        migrations.AlterField(
            model_name='station',
            name='last_updated',
            field=models.DateTimeField(default=None, auto_now=True, null=True),
            preserve_default=True,
        ),
    ]
