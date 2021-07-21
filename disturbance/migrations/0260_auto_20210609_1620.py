# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-06-09 08:20
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0259_auto_20210526_1057'),
    ]

    operations = [
        migrations.AddField(
            model_name='apiarysiteonapproval',
            name='issuance_on_approval',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True),
        ),
    ]
