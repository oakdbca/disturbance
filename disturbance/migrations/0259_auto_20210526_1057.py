# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-05-26 02:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disturbance', '0258_auto_20210524_1025'),
    ]

    operations = [
        migrations.AddField(
            model_name='apiarysiteonapproval',
            name='licensed_site',
            field=models.BooleanField(default=False),
        ),
    ]
