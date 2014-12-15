# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='latency',
            name='ap',
            field=models.ForeignKey(default=None, to='controller.AccessPoint', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='latency',
            name='station',
            field=models.ForeignKey(default=None, to='controller.Station', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='scanresult',
            name='myself_ap',
            field=models.ForeignKey(related_name='myself_ap', default=None, to='controller.AccessPoint', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='scanresult',
            name='myself_station',
            field=models.ForeignKey(related_name='myself_station', default=None, to='controller.Station', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='scanresult',
            name='neighbor',
            field=models.ForeignKey(related_name='neighbor', default=None, to='controller.AccessPoint', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='station',
            name='associate_with',
            field=models.ForeignKey(related_name='associated_stations', default=None, to='controller.AccessPoint', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='throughput',
            name='ap',
            field=models.ForeignKey(default=None, to='controller.AccessPoint', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='throughput',
            name='station',
            field=models.ForeignKey(default=None, to='controller.Station', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='traffic',
            name='ap',
            field=models.ForeignKey(default=None, to='controller.AccessPoint', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='traffic',
            name='hear_by',
            field=models.ForeignKey(related_name='heard_traffic', default=None, to='controller.Station', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='traffic',
            name='station',
            field=models.ForeignKey(default=None, to='controller.Station', null=True),
            preserve_default=True,
        ),
    ]
