# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AccessPoint',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('BSSID', models.CharField(default=None, max_length=17, null=True)),
                ('SSID', models.CharField(default=None, max_length=64, null=True)),
                ('channel', models.IntegerField(default=None, null=True)),
                ('client_num', models.IntegerField(default=None, null=True)),
                ('load', models.FloatField(default=None, null=True)),
                ('sniffer_ap', models.BooleanField(default=False)),
                ('MAC', models.CharField(default=None, max_length=17, null=True)),
                ('IP', models.CharField(default=None, max_length=128, null=True)),
                ('tx_power', models.IntegerField(default=None, null=True)),
                ('noise', models.IntegerField(default=None, null=True)),
                ('enabled', models.BooleanField(default=True)),
                ('last_status_update', models.DateTimeField(default=None, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Latency',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(default=None, null=True)),
                ('host', models.CharField(default=None, max_length=128)),
                ('packet_transmitted', models.IntegerField(default=None, null=True)),
                ('packet_received', models.IntegerField(default=None, null=True)),
                ('min_rtt', models.FloatField(default=None, null=True)),
                ('max_rtt', models.FloatField(default=None, null=True)),
                ('avg_rtt', models.FloatField(default=None, null=True)),
                ('std_dev', models.FloatField(default=None, null=True)),
                ('ap', models.ForeignKey(to='controller.AccessPoint')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ScanResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('signal', models.IntegerField(default=None, null=True)),
                ('timestamp', models.DateTimeField(default=None, null=True)),
                ('myself_ap', models.ForeignKey(related_name='myself_ap', to='controller.AccessPoint')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Station',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('MAC', models.CharField(default=None, max_length=17)),
                ('sniffer_station', models.BooleanField(default=False)),
                ('phonelab_station', models.BooleanField(default=False)),
                ('inactive_time', models.IntegerField(default=None, null=True)),
                ('rx_bytes', models.BigIntegerField(default=None, null=True)),
                ('rx_packets', models.BigIntegerField(default=None, null=True)),
                ('tx_bytes', models.BigIntegerField(default=None, null=True)),
                ('tx_packets', models.BigIntegerField(default=None, null=True)),
                ('tx_retries', models.BigIntegerField(default=None, null=True)),
                ('tx_fails', models.BigIntegerField(default=None, null=True)),
                ('signal_avg', models.IntegerField(default=None, null=True)),
                ('tx_bitrate_mbps', models.IntegerField(default=None, null=True)),
                ('associate_with', models.ForeignKey(related_name='associated_stations', to='controller.AccessPoint')),
                ('scan_results', models.ManyToManyField(related_name='visible_stations', through='controller.ScanResult', to='controller.AccessPoint')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Throughput',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(default=None, null=True)),
                ('url', models.CharField(default=None, max_length=512, null=True)),
                ('success', models.BooleanField(default=False)),
                ('file_size', models.IntegerField(default=None, null=True)),
                ('duration', models.IntegerField(default=None, null=True)),
                ('throughput', models.FloatField(default=None, null=True)),
                ('ap', models.ForeignKey(to='controller.AccessPoint')),
                ('station', models.ForeignKey(to='controller.Station')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Traffic',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('begin', models.DateTimeField(default=None, null=True)),
                ('end', models.DateTimeField(default=None, null=True)),
                ('tx_bytes', models.BigIntegerField(default=None, null=True)),
                ('rx_bytes', models.BigIntegerField(default=None, null=True)),
                ('avg_signal', models.IntegerField(default=None, null=True)),
                ('timestamp', models.DateTimeField(default=None, null=True)),
                ('ap', models.ForeignKey(to='controller.AccessPoint')),
                ('hear_by', models.ForeignKey(related_name='heard_traffic', to='controller.Station')),
                ('station', models.ForeignKey(to='controller.Station')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='station',
            name='traffics',
            field=models.ManyToManyField(related_name='station_traffic', through='controller.Traffic', to='controller.AccessPoint'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='scanresult',
            name='myself_station',
            field=models.ForeignKey(related_name='myself_station', to='controller.Station'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='scanresult',
            name='neighbor',
            field=models.ForeignKey(related_name='neighbor', to='controller.AccessPoint'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='latency',
            name='station',
            field=models.ForeignKey(to='controller.Station'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='accesspoint',
            name='neighbor_aps',
            field=models.ManyToManyField(to='controller.AccessPoint', through='controller.ScanResult'),
            preserve_default=True,
        ),
    ]
