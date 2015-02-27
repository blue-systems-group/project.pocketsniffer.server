# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('controller', '0023_auto_20150225_0215'),
    ]

    operations = [
        migrations.AlterField(
            model_name='algorithmhistory',
            name='ap',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, default=None, to='controller.AccessPoint', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='latencyresult',
            name='station',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, default=None, to='controller.Station', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='scanresult',
            name='myself_ap',
            field=models.ForeignKey(related_name='myself_ap', on_delete=django.db.models.deletion.SET_NULL, default=None, to='controller.AccessPoint', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='scanresult',
            name='myself_station',
            field=models.ForeignKey(related_name='myself_station', on_delete=django.db.models.deletion.SET_NULL, default=None, to='controller.Station', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='scanresult',
            name='neighbor',
            field=models.ForeignKey(related_name='neighbor', on_delete=django.db.models.deletion.SET_NULL, default=None, to='controller.AccessPoint', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='station',
            name='associate_with',
            field=models.ForeignKey(related_name='associated_stations', on_delete=django.db.models.deletion.SET_NULL, default=None, to='controller.AccessPoint', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='station',
            name='neighbor_station',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, default=None, to='controller.Station', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='throughputresult',
            name='station',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, default=None, to='controller.Station', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='traffic',
            name='hear_by',
            field=models.ForeignKey(related_name='heard_traffic', on_delete=django.db.models.deletion.SET_NULL, default=None, to='controller.Station', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='traffic',
            name='src',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, default=None, to='controller.Station', null=True),
            preserve_default=True,
        ),
    ]
