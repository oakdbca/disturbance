# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-09-15 01:21
from __future__ import unicode_literals

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0156_auto_20200914_1134'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoryDbca',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('wkb_geometry', django.contrib.gis.db.models.fields.MultiPolygonField(blank=True, null=True, srid=4326)),
                ('category_name', models.CharField(blank=True, max_length=20, null=True)),
            ],
        ),
    ]
