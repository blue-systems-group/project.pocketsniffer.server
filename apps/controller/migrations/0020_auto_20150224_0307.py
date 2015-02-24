# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0019_auto_20150223_1821'),
    ]

    operations = [
        migrations.CreateModel(
            name='MeasurementHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('begin1', models.DateTimeField(default=None, null=True)),
                ('end1', models.DateTimeField(default=None, null=True)),
                ('begin2', models.DateTimeField(default=None, null=True)),
                ('end2', models.DateTimeField(default=None, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RemoveField(
            model_name='apconfighistory',
            name='ap',
        ),
        migrations.DeleteModel(
            name='APConfigHistory',
        ),
        migrations.RemoveField(
            model_name='algorithmhistory',
            name='begin',
        ),
        migrations.RemoveField(
            model_name='algorithmhistory',
            name='celery_task_id',
        ),
        migrations.RemoveField(
            model_name='algorithmhistory',
            name='end',
        ),
        migrations.RemoveField(
            model_name='algorithmhistory',
            name='last_updated',
        ),
        migrations.RemoveField(
            model_name='traffic',
            name='for_devices',
        ),
        migrations.AddField(
            model_name='algorithmhistory',
            name='ap',
            field=models.ForeignKey(default=None, to='controller.AccessPoint', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='algorithmhistory',
            name='channel_after',
            field=models.IntegerField(default=None, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='algorithmhistory',
            name='channel_before',
            field=models.IntegerField(default=None, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='algorithmhistory',
            name='channel_dwell_time',
            field=models.IntegerField(default=None, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='algorithmhistory',
            name='timestamp',
            field=models.DateTimeField(auto_now=True, auto_now_add=True, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='station',
            name='neighbor_station',
            field=models.ForeignKey(default=None, to='controller.Station', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='traffic',
            name='for_device',
            field=models.ForeignKey(related_name='for_device', default=None, to='controller.Station', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='algorithmhistory',
            name='algo',
            field=models.CharField(default=None, max_length=128, null=True),
            preserve_default=True,
        ),
    ]
