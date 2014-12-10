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
                ('SSID', models.CharField(default=None, max_length=64, null=True, db_index=True, blank=True)),
                ('BSSID', models.CharField(max_length=17, serialize=False, primary_key=True)),
                ('frequency', models.IntegerField(db_index=True)),
                ('client_num', models.IntegerField(null=True, db_index=True)),
                ('load', models.FloatField(null=True)),
                ('is_sniffer_ap', models.BooleanField(default=False)),
                ('tx_power_dbm', models.IntegerField(null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='NeighborAP',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('signal', models.IntegerField(null=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('myself', models.ForeignKey(related_name='myself', to='controller.AccessPoint')),
                ('neighbor', models.ForeignKey(related_name='neighbor', to='controller.AccessPoint')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ScanResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('signal', models.IntegerField(null=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('ap', models.ForeignKey(to='controller.AccessPoint')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Station',
            fields=[
                ('mac', models.CharField(max_length=17, serialize=False, primary_key=True)),
                ('is_sniffer_client', models.BooleanField(default=False)),
                ('inactive_time', models.IntegerField(null=True)),
                ('rx_bytes', models.BigIntegerField(null=True)),
                ('rx_packets', models.BigIntegerField(null=True)),
                ('tx_bytes', models.BigIntegerField(null=True)),
                ('tx_packets', models.BigIntegerField(null=True)),
                ('tx_retries', models.BigIntegerField(null=True)),
                ('tx_fails', models.BigIntegerField(null=True)),
                ('signal_avg', models.IntegerField(null=True)),
                ('tx_bitrate_mbps', models.IntegerField(null=True)),
                ('associcated_ap', models.ForeignKey(related_name='associated_stations', to='controller.AccessPoint')),
                ('scanned_aps', models.ManyToManyField(related_name='nearby_stations', through='controller.ScanResult', to='controller.AccessPoint')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Traffic',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('begin', models.DateTimeField(null=True)),
                ('end', models.DateTimeField(null=True)),
                ('tx_bytes', models.BigIntegerField(null=True)),
                ('rx_bytes', models.BigIntegerField(null=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('ap', models.ForeignKey(to='controller.AccessPoint')),
                ('station', models.ForeignKey(to='controller.Station')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='scanresult',
            name='station',
            field=models.ForeignKey(to='controller.Station'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='accesspoint',
            name='neighbor_aps',
            field=models.ManyToManyField(to='controller.AccessPoint', through='controller.NeighborAP'),
            preserve_default=True,
        ),
    ]
