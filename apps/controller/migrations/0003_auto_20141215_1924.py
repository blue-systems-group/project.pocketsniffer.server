# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0002_auto_20141215_1832'),
    ]

    operations = [
        migrations.RenameField(
            model_name='station',
            old_name='tx_bitrate_mbps',
            new_name='rx_bitrate',
        ),
        migrations.AddField(
            model_name='station',
            name='IP',
            field=models.CharField(default=None, max_length=128, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='station',
            name='tx_bitrate',
            field=models.IntegerField(default=None, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='station',
            name='MAC',
            field=models.CharField(default=None, max_length=17, null=True),
            preserve_default=True,
        ),
    ]
