# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0021_auto_20150224_1533'),
    ]

    operations = [
        migrations.RenameField(
            model_name='algorithmhistory',
            old_name='timestamp',
            new_name='last_updated',
        ),
        migrations.AddField(
            model_name='latencyresult',
            name='last_updated',
            field=models.DateTimeField(auto_now=True, auto_now_add=True, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='throughputresult',
            name='last_updated',
            field=models.DateTimeField(auto_now=True, auto_now_add=True, null=True),
            preserve_default=True,
        ),
    ]
