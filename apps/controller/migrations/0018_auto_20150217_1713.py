# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0017_auto_20150121_1554'),
    ]

    operations = [
        migrations.CreateModel(
            name='LatencyResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(default=None, null=True)),
                ('pingArgs', models.CharField(default=None, max_length=128, null=True)),
                ('packet_transmitted', models.IntegerField(default=0)),
                ('packet_received', models.IntegerField(default=0)),
                ('min_rtt', models.FloatField(default=0)),
                ('max_rtt', models.FloatField(default=0)),
                ('avg_rtt', models.FloatField(default=0)),
                ('std_dev', models.FloatField(default=0)),
                ('station', models.ForeignKey(to='controller.Station')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ThroughputResult',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(default=None, null=True)),
                ('iperfArgs', models.CharField(default=None, max_length=128, null=True)),
                ('all_bw', models.TextField(default=None, null=True)),
                ('bw', models.FloatField(default=0)),
                ('station', models.ForeignKey(to='controller.Station')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RemoveField(
            model_name='apconfighistory',
            name='timestamp',
        ),
    ]
