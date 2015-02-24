# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0014_auto_20150119_1953'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='traffic',
            name='timestamp',
        ),
        migrations.AddField(
            model_name='algorithmhistory',
            name='last_updated',
            field=models.DateTimeField(default=None, auto_now=True, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='apconfighistory',
            name='last_updated',
            field=models.DateTimeField(default=None, auto_now=True, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='latency',
            name='last_updated',
            field=models.DateTimeField(default=None, auto_now=True, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='scanresult',
            name='last_updated',
            field=models.DateTimeField(default=None, auto_now=True, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='throughput',
            name='last_updated',
            field=models.DateTimeField(default=None, auto_now=True, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='traffic',
            name='last_updated',
            field=models.DateTimeField(default=None, auto_now=True, null=True),
            preserve_default=True,
        ),
    ]
