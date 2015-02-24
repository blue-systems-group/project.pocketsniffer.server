# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0020_auto_20150224_0307'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='accesspoint',
            name='last_status_update',
        ),
        migrations.AddField(
            model_name='accesspoint',
            name='last_updated',
            field=models.DateTimeField(default=None, auto_now=True, null=True),
            preserve_default=True,
        ),
    ]
