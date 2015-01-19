# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0011_traffic_for_sta'),
    ]

    operations = [
        migrations.RenameField(
            model_name='traffic',
            old_name='avg_rx_rssi',
            new_name='avg_rssi',
        ),
        migrations.RenameField(
            model_name='traffic',
            old_name='rx_bytes',
            new_name='packets',
        ),
        migrations.RenameField(
            model_name='traffic',
            old_name='tx_bytes',
            new_name='retry_packets',
        ),
        migrations.RenameField(
            model_name='traffic',
            old_name='from_station',
            new_name='src',
        ),
        migrations.RemoveField(
            model_name='station',
            name='traffics',
        ),
        migrations.RemoveField(
            model_name='traffic',
            name='avg_tx_rssi',
        ),
        migrations.RemoveField(
            model_name='traffic',
            name='to_ap',
        ),
    ]
