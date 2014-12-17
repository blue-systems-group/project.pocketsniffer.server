# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0003_auto_20141215_1924'),
    ]

    operations = [
        migrations.AddField(
            model_name='station',
            name='last_updated',
            field=models.DateTimeField(default=None, null=True),
            preserve_default=True,
        ),
    ]
