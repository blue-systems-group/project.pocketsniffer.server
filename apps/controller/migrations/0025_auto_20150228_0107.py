# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0024_auto_20150226_2059'),
    ]

    operations = [
        migrations.AddField(
            model_name='measurementhistory',
            name='station_map',
            field=models.TextField(default=None, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='accesspoint',
            name='BSSID',
            field=models.CharField(default=None, max_length=17, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='accesspoint',
            name='IP',
            field=models.CharField(default=None, max_length=128, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='accesspoint',
            name='MAC',
            field=models.CharField(default=None, max_length=17, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='accesspoint',
            name='SSID',
            field=models.CharField(default=None, max_length=64, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='accesspoint',
            name='channel',
            field=models.IntegerField(default=None, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='accesspoint',
            name='last_updated',
            field=models.DateTimeField(default=None, auto_now=True, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='accesspoint',
            name='sniffer_ap',
            field=models.BooleanField(default=False, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='algorithmhistory',
            name='algo',
            field=models.CharField(default=None, max_length=128, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='algorithmhistory',
            name='channel_after',
            field=models.IntegerField(default=None, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='algorithmhistory',
            name='channel_before',
            field=models.IntegerField(default=None, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='algorithmhistory',
            name='last_updated',
            field=models.DateTimeField(auto_now=True, auto_now_add=True, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='latencyresult',
            name='avg_rtt',
            field=models.FloatField(default=0, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='latencyresult',
            name='last_updated',
            field=models.DateTimeField(auto_now=True, auto_now_add=True, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='latencyresult',
            name='max_rtt',
            field=models.FloatField(default=0, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='latencyresult',
            name='min_rtt',
            field=models.FloatField(default=0, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='latencyresult',
            name='std_dev',
            field=models.FloatField(default=0, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='latencyresult',
            name='timestamp',
            field=models.DateTimeField(default=None, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='measurementhistory',
            name='algo',
            field=models.CharField(default=None, max_length=128, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='measurementhistory',
            name='begin1',
            field=models.DateTimeField(default=None, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='measurementhistory',
            name='measurement',
            field=models.CharField(default=None, max_length=128, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='scanresult',
            name='last_updated',
            field=models.DateTimeField(default=None, auto_now=True, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='station',
            name='IP',
            field=models.CharField(default=None, max_length=128, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='station',
            name='MAC',
            field=models.CharField(default=None, max_length=17, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='station',
            name='last_updated',
            field=models.DateTimeField(default=None, auto_now=True, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='station',
            name='phonelab_station',
            field=models.BooleanField(default=False, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='station',
            name='sniffer_station',
            field=models.BooleanField(default=False, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='throughputresult',
            name='bw',
            field=models.FloatField(default=0, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='throughputresult',
            name='last_updated',
            field=models.DateTimeField(auto_now=True, auto_now_add=True, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='throughputresult',
            name='timestamp',
            field=models.DateTimeField(default=None, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='traffic',
            name='begin',
            field=models.DateTimeField(default=None, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='traffic',
            name='channel',
            field=models.IntegerField(default=None, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='traffic',
            name='end',
            field=models.DateTimeField(default=None, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='traffic',
            name='last_updated',
            field=models.DateTimeField(default=None, auto_now=True, null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='traffic',
            name='packets',
            field=models.BigIntegerField(default=None, null=True, db_index=True),
            preserve_default=True,
        ),
    ]
