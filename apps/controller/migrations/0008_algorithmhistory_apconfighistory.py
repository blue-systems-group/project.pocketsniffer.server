# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0007_remove_throughput_ap'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlgorithmHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('algo', models.CharField(max_length=128)),
                ('begin', models.DateTimeField()),
                ('end', models.DateTimeField()),
                ('celery_task_id', models.IntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='APConfigHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField()),
                ('channel', models.IntegerField(default=None, null=True)),
                ('txpower', models.IntegerField(default=None, null=True)),
                ('ap', models.ForeignKey(to='controller.AccessPoint')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
