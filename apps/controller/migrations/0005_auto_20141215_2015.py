# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0004_station_last_updated'),
    ]

    operations = [
        migrations.RenameField(
            model_name='traffic',
            old_name='avg_signal',
            new_name='avg_rx_rssi',
        ),
        migrations.RenameField(
            model_name='traffic',
            old_name='station',
            new_name='from_station',
        ),
        migrations.RenameField(
            model_name='traffic',
            old_name='ap',
            new_name='to_ap',
        ),
        migrations.AddField(
            model_name='traffic',
            name='avg_tx_rssi',
            field=models.IntegerField(default=None, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='traffic',
            name='channel',
            field=models.IntegerField(default=None, null=True),
            preserve_default=True,
        ),
    ]
