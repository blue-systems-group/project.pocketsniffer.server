# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Device',
            fields=[
                ('hashedID', models.CharField(max_length=40, unique=True, serialize=False, primary_key=True)),
                ('state_count', models.IntegerField(default=0)),
                ('manifest_count', models.IntegerField(default=0)),
                ('upload_count', models.IntegerField(default=0)),
                ('upload_bytes_count', models.BigIntegerField(default=0)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Manifest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('retrieved_time', models.DateTimeField()),
                ('version', models.CharField(max_length=10)),
                ('device', models.ForeignKey(to='backend.Device')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='State',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('version_name', models.DecimalField(null=True, max_digits=3, decimal_places=1)),
                ('version_code', models.IntegerField(null=True)),
                ('last_upload', models.DateTimeField(null=True)),
                ('uploaded_bytes', models.BigIntegerField(null=True)),
                ('reason_not_upload', models.CharField(max_length=1024, null=True, blank=True)),
                ('received_time', models.DateTimeField(db_index=True)),
                ('received_ID', models.CharField(max_length=40, null=True)),
                ('version', models.CharField(max_length=10)),
                ('device', models.ForeignKey(to='backend.Device')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Upload',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('received_time', models.DateTimeField()),
                ('version', models.CharField(max_length=10)),
                ('bytes', models.IntegerField()),
                ('packagename', models.CharField(max_length=256, null=True, blank=True)),
                ('upload_filename', models.CharField(max_length=128)),
                ('disabled', models.BooleanField(default=False)),
                ('compressed', models.BooleanField(default=False)),
                ('device', models.ForeignKey(to='backend.Device')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='upload',
            unique_together=set([('device', 'received_time')]),
        ),
        migrations.AlterUniqueTogether(
            name='state',
            unique_together=set([('device', 'received_time')]),
        ),
        migrations.AlterUniqueTogether(
            name='manifest',
            unique_together=set([('device', 'retrieved_time')]),
        ),
        migrations.AddField(
            model_name='device',
            name='last_manifest',
            field=models.ForeignKey(related_name='manifest_device', blank=True, to='backend.Manifest', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='device',
            name='last_state',
            field=models.ForeignKey(related_name='state_device', blank=True, to='backend.State', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='device',
            name='last_upload',
            field=models.ForeignKey(related_name='upload_device', blank=True, to='backend.Upload', null=True),
            preserve_default=True,
        ),
    ]
