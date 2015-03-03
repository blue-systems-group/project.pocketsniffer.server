# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0029_measurementhistory_client_num'),
    ]

    operations = [
        migrations.AddField(
            model_name='traffic',
            name='bytes',
            field=models.BigIntegerField(default=None, null=True),
            preserve_default=True,
        ),
    ]
